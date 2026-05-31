/**
 * Generates from backend/openapi.yaml:
 *
 *   object-schema layer — split into three categories:
 *     apps/studio-app/src/api/generated/object-schema/requests.gen.ts       (interfaces + Constraints for *Request / *In)
 *     apps/studio-app/src/api/generated/object-schema/requests.zod.gen.ts   (Zod schemas for requests)
 *     apps/studio-app/src/api/generated/object-schema/responses.gen.ts      (interfaces + Constraints for *Responses)
 *     apps/studio-app/src/api/generated/object-schema/responses.zod.gen.ts  (Zod schemas for responses)
 *     apps/studio-app/src/api/generated/object-schema/subtypes.gen.ts       (interfaces + Constraints for everything else)
 *     apps/studio-app/src/api/generated/object-schema/subtypes.zod.gen.ts   (Zod schemas for subtypes)
 *
 *   endpoint layer (one folder per tag, one file per concern):
 *     apps/studio-app/src/api/generated/endpoints/<tag>/types.gen.ts
 *     apps/studio-app/src/api/generated/endpoints/<tag>/requests.gen.ts
 *     apps/studio-app/src/api/generated/endpoints/<tag>/hooks.gen.ts
 *
 * The hand-authored api-schema/schema.ts is kept separate (openapi-typescript).
 *
 * Run from the frontend/ directory:
 *   node scripts/generate-types.mjs
 */

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import yaml from "js-yaml";

const __dirname = dirname(fileURLToPath(import.meta.url));
const specPath = resolve(__dirname, "../../backend/openapi.yaml");
const generatedRoot = resolve(
  __dirname,
  "../apps/studio-app/src/api/generated",
);
const objectSchemaDir = `${generatedRoot}/object-schema`;
const endpointsDir = `${generatedRoot}/endpoints`;

mkdirSync(objectSchemaDir, { recursive: true });

const spec = yaml.load(readFileSync(specPath, "utf8"));
const allSchemas = spec.components?.schemas ?? {};

// OpenAPI infrastructure schemas — skip for domain codegen
const SKIP = new Set(["ErrorResponse"]);

/** Classify a schema name into request | response | subtype */
function schemaCategory(name) {
  if (name.endsWith("Request") || name.endsWith("In")) return "request";
  if (name.endsWith("Responses")) return "response";
  return "subtype";
}

const domainEntries = Object.entries(allSchemas).filter(
  ([name]) => !SKIP.has(name),
);
const sorted = topoSort(domainEntries, allSchemas);

// All named types come from schema.ts (openapi-typescript output).
// object-schema/*.gen.ts only emits Constraints and Zod schemas now.
const schemaSourceFile = {};
for (const [name] of domainEntries) {
  schemaSourceFile[name] = `../../schema`;
}

// ─── object-schema: Constraints + Zod for requests and subtypes only ─────────
// Interfaces live in schema.ts (openapi-typescript). Responses need neither.

const CATEGORIES = ["request", "subtype"];

for (const category of CATEGORIES) {
  const subset = sorted.filter(([name]) => schemaCategory(name) === category);

  // ── <category>s.gen.ts — Constraints only ────────────────────────────────
  const constraintLines = ["// This file is auto-generated — do not edit manually", ""];

  for (const [name, schema] of subset) {
    if (!schema.properties) continue;
    const props = schema.properties;
    const constraints = buildConstraints(props);
    if (Object.keys(constraints).length > 0) {
      constraintLines.push(`export const ${name}Constraints = {`);
      for (const [field, c] of Object.entries(constraints)) {
        const entries = Object.entries(c)
          .map(([k, v]) => `${k}: ${k === "pattern" ? `/${v}/` : JSON.stringify(v)}`)
          .join(", ");
        constraintLines.push(`  ${field}: { ${entries} },`);
      }
      constraintLines.push(`} as const;`);
      constraintLines.push("");
    }
  }

  const typesFile = `${objectSchemaDir}/${category}s.gen.ts`;
  writeFileSync(typesFile, constraintLines.join("\n"));
  console.log(`Generated ${typesFile}`);

  // ── <category>s.zod.gen.ts ────────────────────────────────────────────────
  const zodLines = ["// This file is auto-generated — do not edit manually", "", 'import { z } from "zod";', ""];

  // Cross-category Zod imports — sibling *.zod.gen.ts files
  const zodCrossImports = new Map(); // zodSrc -> Set of zNames
  for (const [, schema] of subset) {
    for (const ref of refsInSchema(schema)) {
      if (SKIP.has(ref)) continue;
      const refCategory = schemaCategory(ref);
      if (refCategory !== category) {
        const zodSrc = `./${refCategory}s.zod.gen`;
        if (!zodCrossImports.has(zodSrc)) zodCrossImports.set(zodSrc, new Set());
        zodCrossImports.get(zodSrc).add(`z${ref}`);
      }
    }
  }
  for (const [zodSrc, zNames] of zodCrossImports) {
    zodLines.push(`import { ${[...zNames].sort().join(", ")} } from "${zodSrc}";`);
  }
  if (zodCrossImports.size > 0) zodLines.push("");

  for (const [name, schema] of subset) {
    if (!schema.properties && (schema.oneOf || schema.anyOf)) {
      const variants = schema.oneOf ?? schema.anyOf;
      if (schema.discriminator) {
        const prop = schema.discriminator.propertyName;
        const refs = variants.filter((v) => v.$ref).map((v) => `z${v.$ref.split("/").pop()}`);
        zodLines.push(`export const z${name} = z.discriminatedUnion("${prop}", [${refs.join(", ")}]);`);
      } else {
        const exprs = variants.map((v) => v.$ref ? `z${v.$ref.split("/").pop()}` : buildZodExpr(v, allSchemas));
        zodLines.push(`export const z${name} = z.union([${exprs.join(", ")}]);`);
      }
      zodLines.push("");
      continue;
    }

    const props = schema.properties ?? {};
    const required = new Set(schema.required ?? []);
    // Fields with a default are always present — treat as required to match openapi-typescript
    for (const [field, def] of Object.entries(props)) {
      if (def.default !== undefined) required.add(field);
    }

    zodLines.push(`export const z${name} = z.object({`);
    for (const [field, def] of Object.entries(props)) {
      zodLines.push(`  ${field}: ${resolveZodType(def, required.has(field), allSchemas)},`);
    }
    zodLines.push(`});`);
    zodLines.push("");
  }

  const zodFile = `${objectSchemaDir}/${category}s.zod.gen.ts`;
  writeFileSync(zodFile, zodLines.join("\n"));
  console.log(`Generated ${zodFile}`);
}

// ─── rbac.gen.ts — permission union + operationId map ────────────────────────

const allPermissions = new Set();
const operationPermissionEntries = [];

for (const [path, methods] of Object.entries(spec.paths ?? {})) {
  for (const [, op] of Object.entries(methods)) {
    const permission = op["x-flowform-rbac"]?.permission ?? null;
    if (permission) allPermissions.add(permission);
    if (op.operationId) {
      operationPermissionEntries.push([op.operationId, permission]);
    }
  }
}

const rbacLines = ["// This file is auto-generated — do not edit manually", ""];

if (allPermissions.size > 0) {
  const permLiterals = [...allPermissions].sort().map((p) => `  | "${p}"`).join("\n");
  rbacLines.push(`export type FlowFormPermission =\n${permLiterals};`);
  rbacLines.push("");
}

rbacLines.push(`export const operationPermissions: Record<string, FlowFormPermission | null> = {`);
for (const [opId, perm] of operationPermissionEntries.sort(([a], [b]) => a.localeCompare(b))) {
  rbacLines.push(`  ${opId}: ${perm ? `"${perm}"` : "null"},`);
}
rbacLines.push(`};`);
rbacLines.push("");

// routePermissions: array of [method, regexSource, permission, paramNames]
// Used by the middleware to match a live URL back to a required permission.
// {param} segments become named capture groups so project_id / survey_id can be extracted.
const routePermissionEntries = [];
for (const [path, methods] of Object.entries(spec.paths ?? {})) {
  for (const [method, op] of Object.entries(methods)) {
    const permission = op["x-flowform-rbac"]?.permission ?? null;
    if (!permission) continue;
    // Convert /api/v1/projects/{project_id}/surveys/{survey_id} ->
    //   regex: /api/v1/projects/(?<project_id>\d+)/surveys/(?<survey_id>\d+)
    const paramNames = [];
    const regexStr = path
      .replace(/\{(\w+)\}/g, (_, name) => { paramNames.push(name); return `(?<${name}>[^/]+)`; })
      .replace(/\//g, "\\/");
    routePermissionEntries.push({ method: method.toUpperCase(), regexStr, permission, paramNames });
  }
}

rbacLines.push(`export type RoutePermissionEntry = {`);
rbacLines.push(`  method: string;`);
rbacLines.push(`  pattern: RegExp;`);
rbacLines.push(`  permission: FlowFormPermission;`);
rbacLines.push(`  paramNames: string[];`);
rbacLines.push(`};`);
rbacLines.push("");
rbacLines.push(`export const routePermissions: RoutePermissionEntry[] = [`);
for (const { method, regexStr, permission, paramNames } of routePermissionEntries) {
  rbacLines.push(`  { method: "${method}", pattern: /^${regexStr}$/, permission: "${permission}", paramNames: ${JSON.stringify(paramNames)} },`);
}
rbacLines.push(`];`);
rbacLines.push("");

const rbacFile = `${generatedRoot}/rbac.gen.ts`;
writeFileSync(rbacFile, rbacLines.join("\n"));
console.log(`Generated ${rbacFile}`);

// ─── Endpoint layer — one folder per tag ─────────────────────────────────────

// Collect every operation grouped by its first tag
/** @type {Map<string, Array>} */
const byTag = new Map();

for (const [path, methods] of Object.entries(spec.paths ?? {})) {
  for (const [method, op] of Object.entries(methods)) {
    const tag = (op.tags?.[0] ?? "misc").toLowerCase().replace(/\s+/g, "-");
    if (!byTag.has(tag)) byTag.set(tag, []);
    byTag.get(tag).push({ path, method: method.toUpperCase(), op });
  }
}

for (const [tag, ops] of byTag) {
  const tagDir = `${endpointsDir}/${tag}`;
  mkdirSync(tagDir, { recursive: true });

  // Collect types used by this tag's operations
  const usedTypes = new Set();
  for (const { op } of ops) {
    const body = bodyTypeName(op);
    const resp = responseTypeName(op);
    if (body) usedTypes.add(body);
    if (resp && resp !== "void") {
      // strip [] suffix — the base type name is what we import
      usedTypes.add(resp.replace("[]", ""));
    }
  }

  // ── types.gen.ts ──────────────────────────────────────────────────────────
  // Group used types by their source category file
  const typesBySource = new Map();
  for (const typeName of usedTypes) {
    const src = schemaSourceFile[typeName] ?? "../../object-schema/subtypes.gen";
    if (!typesBySource.has(src)) typesBySource.set(src, new Set());
    typesBySource.get(src).add(typeName);
  }

  const typesLines = ["// This file is auto-generated — do not edit manually", ""];
  for (const [src, names] of [...typesBySource].sort(([a], [b]) => a.localeCompare(b))) {
    typesLines.push(`export type { ${[...names].sort().join(", ")} } from "${src}";`);
  }
  typesLines.push("");
  writeFileSync(`${tagDir}/types.gen.ts`, typesLines.join("\n"));

  // ── requests.gen.ts ───────────────────────────────────────────────────────
  const reqLines = [
    "// This file is auto-generated — do not edit manually",
    "",
    `import type { OpenApiFetchClient } from "../../../openapi";`,
  ];
  if (usedTypes.size > 0) {
    reqLines.push(
      `import type { ${[...usedTypes].sort().join(", ")} } from "./types.gen";`,
    );
  }
  reqLines.push("");

  for (const { path, method, op } of ops) {
    const fnName = op.operationId;
    const pathParams = pathParamsFor(op);
    const queryParams = queryParamsFor(op);
    const bodyName = bodyTypeName(op);
    const respName = responseTypeName(op) ?? "void";

    // Function signature args: path params first, then query object, then body
    const args = [
      "apiClient: OpenApiFetchClient",
      ...pathParams.map(({ name, schema }) => `${name}: ${paramTsType(schema)}`),
    ];
    if (queryParams.length > 0) {
      const anyRequired = queryParams.some((p) => p.required);
      const fields = queryParams
        .map(({ name, schema, required }) => {
          const tsType = paramTsType(schema);
          return `${name}${required ? "" : "?"}: ${tsType}`;
        })
        .join("; ");
      args.push(`query${anyRequired ? "" : "?"}: { ${fields} }`);
    }
    if (bodyName) args.push(`body: ${bodyName}`);

    reqLines.push(
      `export async function ${fnName}(${args.join(", ")}): Promise<${respName}> {`,
    );

    // Build the openapi-fetch call options
    const pathObj =
      pathParams.length > 0
        ? `{ ${pathParams.map((p) => p.name).join(", ")} }`
        : null;
    const optParts = [];
    if (pathObj) optParts.push(`path: ${pathObj}`);
    if (queryParams.length > 0) optParts.push(`query: query ?? {}`);

    const callOpts = [];
    if (optParts.length > 0) callOpts.push(`params: { ${optParts.join(", ")} }`);
    if (bodyName) callOpts.push("body: body as never");

    const optsStr =
      callOpts.length > 0
        ? `, { ${callOpts.join(", ")} }`
        : "";

    if (respName === "void") {
      reqLines.push(
        `  const { error } = await apiClient.${method}(\`${path}\`${optsStr});`,
      );
      reqLines.push(`  if (error) throw error;`);
    } else {
      reqLines.push(
        `  const { data, error } = await apiClient.${method}(\`${path}\`${optsStr});`,
      );
      reqLines.push(`  if (error) throw error;`);
      reqLines.push(`  return data;`);
    }
    reqLines.push(`}`);
    reqLines.push("");
  }

  writeFileSync(`${tagDir}/requests.gen.ts`, reqLines.join("\n"));

  // ── hooks.gen.ts ──────────────────────────────────────────────────────────
  const fnNames = ops.map((o) => o.op.operationId);
  const hasMutations = ops.some(({ method }) => method !== "GET");
  const hasQueries = ops.some(({ method }) => method === "GET");
  const rqImports = [
    hasMutations && "useMutation",
    hasQueries && "useQuery",
    hasMutations && "useQueryClient",
  ].filter(Boolean).join(", ");
  const hookLines = [
    "// This file is auto-generated — do not edit manually",
    "",
    `import { ${rqImports} } from "@tanstack/react-query";`,
    `import { useOpenApiClient } from "../../../openapi";`,
  ];
  // Hooks only need body (request) types — response types are inferred
  const hookBodyTypes = new Set(
    ops.map(({ op }) => bodyTypeName(op)).filter(Boolean),
  );
  if (hookBodyTypes.size > 0) {
    hookLines.push(
      `import type { ${[...hookBodyTypes].sort().join(", ")} } from "./types.gen";`,
    );
  }
  hookLines.push(
    `import { ${fnNames.join(", ")} } from "./requests.gen";`,
  );
  hookLines.push("");

  // Query key object — one entry per list operation, one for detail
  const keyName = tagToKeyName(tag);
  hookLines.push(`export const ${keyName} = {`);
  hookLines.push(`  all: () => ["${tag}"] as const,`);

  // find list and detail GET operations to give them named keys
  const listOps = ops.filter(
    ({ method, op }) => method === "GET" && !op.operationId.startsWith("get"),
  );
  const detailOps = ops.filter(
    ({ method, op }) => method === "GET" && op.operationId.startsWith("get"),
  );
  // Only emit one `list` key — use the first list op
  if (listOps.length > 0) {
    const pathParams = pathParamsFor(listOps[0].op);
    if (pathParams.length > 0) {
      const args = pathParams.map((p) => `${p.name}: ${paramTsType(p.schema)}`).join(", ");
      const spread = pathParams.map((p) => p.name).join(", ");
      hookLines.push(
        `  list: (${args}) => [...${keyName}.all(), "list", ${spread}] as const,`,
      );
    } else {
      hookLines.push(
        `  list: () => [...${keyName}.all(), "list"] as const,`,
      );
    }
  }
  // Only emit one `detail` key — use the first detail op with path params
  const firstDetailOp = detailOps.find(({ op }) => pathParamsFor(op).length > 0);
  if (firstDetailOp) {
    const pathParams = pathParamsFor(firstDetailOp.op);
    const args = pathParams.map((p) => `${p.name}: ${paramTsType(p.schema)}`).join(", ");
    const spread = pathParams.map((p) => p.name).join(", ");
    hookLines.push(
      `  detail: (${args}) => [...${keyName}.all(), "detail", ${spread}] as const,`,
    );
  }
  hookLines.push(`};`);
  hookLines.push("");

  // Generate one hook per operation
  for (const { method, op } of ops) {
    const fnName = op.operationId;
    const hookName = "use" + fnName.charAt(0).toUpperCase() + fnName.slice(1);
    const pathParams = pathParamsFor(op);
    const queryParams = queryParamsFor(op);
    const bodyName = bodyTypeName(op);
    const respName = responseTypeName(op) ?? "void";
    const isArray = respName.endsWith("[]");
    const baseType = respName.replace("[]", "");

    const hookArgs = [
      ...pathParams.map(({ name, schema }) => `${name}: ${paramTsType(schema)}`),
    ];
    if (queryParams.length > 0) {
      const anyRequired = queryParams.some((p) => p.required);
      const fields = queryParams
        .map(({ name, schema, required }) => {
          const tsType = paramTsType(schema);
          return `${name}${required ? "" : "?"}: ${tsType}`;
        })
        .join("; ");
      hookArgs.push(`query${anyRequired ? "" : "?"}: { ${fields} }`);
    }

    if (method === "GET") {
      const hasListKey = listOps.some((o) => o.op.operationId === fnName);
      const hasDetailKey = detailOps.some((o) => o.op.operationId === fnName);
      let queryKeyExpr;
      if (hasListKey && pathParams.length > 0) {
        queryKeyExpr = `${keyName}.list(${pathParams.map((p) => p.name).join(", ")})`;
      } else if (hasListKey) {
        queryKeyExpr = `${keyName}.list()`;
      } else if (hasDetailKey && pathParams.length > 0) {
        queryKeyExpr = `${keyName}.detail(${pathParams.map((p) => p.name).join(", ")})`;
      } else {
        queryKeyExpr = `${keyName}.all()`;
      }

      const callArgs = [
        "apiClient",
        ...pathParams.map((p) => p.name),
        ...(queryParams.length > 0 ? ["query"] : []),
      ].join(", ");

      const enabledParts = pathParams.map((p) =>
        paramTsType(p.schema) === "number" ? `${p.name} > 0` : `!!${p.name}`,
      );
      const enabledExpr =
        enabledParts.length > 0 ? enabledParts.join(" && ") : null;

      hookLines.push(
        `export function ${hookName}(${hookArgs.join(", ")}) {`,
      );
      hookLines.push(`  const apiClient = useOpenApiClient();`);
      hookLines.push(`  return useQuery({`);
      hookLines.push(`    queryKey: ${queryKeyExpr},`);
      hookLines.push(
        `    queryFn: () => ${fnName}(${callArgs}),`,
      );
      if (enabledExpr) {
        hookLines.push(`    enabled: ${enabledExpr},`);
      }
      hookLines.push(`  });`);
      hookLines.push(`}`);
    } else {
      // Mutation — build mutationFn arg shape
      const mutArgs = [];
      const callArgs = ["apiClient"];

      // path params come from the hook closure
      for (const p of pathParams) callArgs.push(p.name);
      // query params from hook closure too
      if (queryParams.length > 0) callArgs.push("query");

      if (bodyName) {
        mutArgs.push(`body: ${bodyName}`);
        callArgs.push("body");
      }

      // If there are extra path params NOT in the hook args (e.g. item id
      // passed per-mutation like nodeId), they come in the mutation arg.
      // Detect: path params not already in hookArgs (which are the context params)
      // For simplicity: if no body and path params are the only inputs, pass
      // the last path param as the mutation arg (covers DELETE with id).
      const contextParams = pathParams; // all path params are context for now

      hookLines.push(
        `export function ${hookName}(${hookArgs.join(", ")}) {`,
      );
      hookLines.push(`  const apiClient = useOpenApiClient();`);
      hookLines.push(`  const queryClient = useQueryClient();`);
      hookLines.push(`  return useMutation({`);

      if (mutArgs.length > 0) {
        hookLines.push(
          `    mutationFn: (${mutArgs.join(", ")}) => ${fnName}(${callArgs.join(", ")}),`,
        );
      } else {
        hookLines.push(
          `    mutationFn: () => ${fnName}(${callArgs.join(", ")}),`,
        );
      }

      // onSuccess: invalidate the tag's list key using the list op's own path params
      const listOpParams = listOps.length > 0 ? pathParamsFor(listOps[0].op) : [];
      const listKey =
        listOps.length > 0
          ? listOpParams.length > 0
            ? `${keyName}.list(${listOpParams.map((p) => p.name).join(", ")})`
            : `${keyName}.list()`
          : `${keyName}.all()`;

      hookLines.push(`    onSuccess: () => {`);
      hookLines.push(
        `      void queryClient.invalidateQueries({ queryKey: ${listKey} });`,
      );
      hookLines.push(`    },`);
      hookLines.push(`  });`);
      hookLines.push(`}`);
    }

    hookLines.push("");
  }

  writeFileSync(`${tagDir}/hooks.gen.ts`, hookLines.join("\n"));
  console.log(`Generated ${tagDir}/`);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Collect all $ref names reachable one level deep in a schema node. */
function refsInSchema(schema) {
  if (!schema || typeof schema !== "object") return [];
  const refs = [];
  if (schema.$ref) refs.push(schema.$ref.split("/").pop());
  for (const list of [schema.anyOf, schema.oneOf, schema.allOf]) {
    if (Array.isArray(list)) list.forEach((v) => refs.push(...refsInSchema(v)));
  }
  if (schema.items) refs.push(...refsInSchema(schema.items));
  for (const v of Object.values(schema.properties ?? {})) refs.push(...refsInSchema(v));
  return refs;
}

function topoSort(entries, allSchemas) {
  const nameToEntry = Object.fromEntries(entries);
  const visited = new Set();
  const result = [];

  function visit(name) {
    if (visited.has(name)) return;
    visited.add(name);
    const schema = allSchemas[name];
    if (!schema) return;
    for (const ref of refsInSchema(schema)) {
      if (nameToEntry[ref]) visit(ref);
    }
    if (nameToEntry[name]) result.push([name, nameToEntry[name]]);
  }

  for (const [name] of entries) visit(name);
  return result;
}

function resolveType(def, allSchemas) {
  if (!def) return "unknown";
  if (def.$ref) return def.$ref.split("/").pop();
  if (def.anyOf) {
    const nonNull = def.anyOf.filter((v) => v.type !== "null");
    const nullable = nonNull.length < def.anyOf.length;
    const inner = nonNull.map((v) => resolveType(v, allSchemas)).join(" | ");
    return nullable ? `${inner} | null` : inner;
  }
  if (def.oneOf) return def.oneOf.map((v) => resolveType(v, allSchemas)).join(" | ");
  if (def.allOf) return def.allOf.map((v) => resolveType(v, allSchemas)).join(" & ");
  if (def.const !== undefined) return JSON.stringify(def.const);
  if (def.type === "array") {
    const item = def.items ? resolveType(def.items, allSchemas) : "unknown";
    const needsParens = item.includes(" | ") || item.includes(" & ");
    return needsParens ? `(${item})[]` : `${item}[]`;
  }
  if (def.enum) return def.enum.map((v) => JSON.stringify(v)).join(" | ");
  if (def.type === "integer" || def.type === "number") return "number";
  if (def.type === "boolean") return "boolean";
  if (def.type === "string") return "string";
  if (def.type === "object") return "Record<string, unknown>";
  if (def.type === "null") return "null";
  return "unknown";
}

function resolveZodType(def, isRequired, allSchemas) {
  let expr = buildZodExpr(def, allSchemas);
  if (!isRequired) expr += ".optional()";
  return expr;
}

function buildZodExpr(def, allSchemas) {
  if (!def) return "z.unknown()";
  if (def.$ref) return `z${def.$ref.split("/").pop()}`;
  if (def.anyOf) {
    const nonNull = def.anyOf.filter((v) => v.type !== "null");
    const nullable = nonNull.length < def.anyOf.length;
    if (nonNull.length === 1) {
      const inner = buildZodExpr(nonNull[0], allSchemas);
      return nullable ? `${inner}.nullable()` : inner;
    }
    const exprs = nonNull.map((v) => buildZodExpr(v, allSchemas));
    const union = `z.union([${exprs.join(", ")}])`;
    return nullable ? `${union}.nullable()` : union;
  }
  if (def.oneOf) {
    if (def.discriminator) {
      const prop = def.discriminator.propertyName;
      const refs = def.oneOf
        .filter((v) => v.$ref)
        .map((v) => `z${v.$ref.split("/").pop()}`);
      return `z.discriminatedUnion("${prop}", [${refs.join(", ")}])`;
    }
    const exprs = def.oneOf.map((v) => buildZodExpr(v, allSchemas));
    return `z.union([${exprs.join(", ")}])`;
  }
  if (def.allOf) {
    const exprs = def.allOf.map((v) => buildZodExpr(v, allSchemas));
    return exprs.reduce((acc, e) => `${acc}.merge(${e})`);
  }
  if (def.const !== undefined) return `z.literal(${JSON.stringify(def.const)})`;
  if (def.type === "array") {
    const itemExpr = def.items ? buildZodExpr(def.items, allSchemas) : "z.unknown()";
    let expr = `z.array(${itemExpr})`;
    if (def.minItems !== undefined) expr += `.min(${def.minItems})`;
    if (def.maxItems !== undefined) expr += `.max(${def.maxItems})`;
    return expr;
  }
  if (def.enum) {
    const literals = def.enum.map((v) => `z.literal(${JSON.stringify(v)})`);
    return literals.length === 1 ? literals[0] : `z.union([${literals.join(", ")}])`;
  }
  if (def.type === "integer") {
    let expr = "z.number().int()";
    if (def.minimum !== undefined) expr += `.gte(${def.minimum})`;
    if (def.maximum !== undefined) expr += `.lte(${def.maximum})`;
    return expr;
  }
  if (def.type === "number") {
    let expr = "z.number()";
    if (def.minimum !== undefined) expr += `.gte(${def.minimum})`;
    if (def.maximum !== undefined) expr += `.lte(${def.maximum})`;
    return expr;
  }
  if (def.type === "boolean") return "z.boolean()";
  if (def.type === "string") {
    let expr = "z.string()";
    if (def.minLength !== undefined) expr += `.min(${def.minLength})`;
    if (def.maxLength !== undefined) expr += `.max(${def.maxLength})`;
    if (def.pattern !== undefined) expr += `.regex(/${def.pattern}/)`;
    return expr;
  }
  if (def.type === "object") return "z.record(z.string(), z.unknown())";
  if (def.type === "null") return "z.null()";
  return "z.unknown()";
}

function buildConstraints(props) {
  const KEYS = [
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
  ];
  const result = {};
  for (const [field, def] of Object.entries(props)) {
    const effective =
      def.anyOf ? (def.anyOf.find((v) => v.type !== "null") ?? def) : def;
    const c = {};
    for (const key of KEYS) {
      if (effective[key] !== undefined) c[key] = effective[key];
    }
    if (Object.keys(c).length > 0) result[field] = c;
  }
  return result;
}

/** Extract path parameters from an operation. */
function pathParamsFor(op) {
  return (op.parameters ?? [])
    .filter((p) => p.in === "path")
    .map((p) => ({ name: p.name, schema: p.schema ?? {} }));
}

/** Extract query parameters from an operation. */
function queryParamsFor(op) {
  return (op.parameters ?? [])
    .filter((p) => p.in === "query")
    .map((p) => ({ name: p.name, schema: p.schema ?? {}, required: p.required ?? false }));
}

/** Resolve the body schema name, or null if none. */
function bodyTypeName(op) {
  const ref = op.requestBody?.content?.["application/json"]?.schema?.$ref;
  if (!ref) return null;
  const name = ref.split("/").pop();
  return SKIP.has(name) ? null : name;
}

/**
 * Resolve the success response type name (with [] suffix for arrays), or null.
 * Returns "void" for 204.
 */
function responseTypeName(op) {
  for (const [code, response] of Object.entries(op.responses ?? {})) {
    if (!code.startsWith("2")) continue;
    if (code === "204") return "void";
    const sc = response?.content?.["application/json"]?.schema;
    if (!sc) return null;
    if (sc.$ref) {
      const name = sc.$ref.split("/").pop();
      return SKIP.has(name) ? null : name;
    }
    if (sc.type === "array" && sc.items?.$ref) {
      const name = sc.items.$ref.split("/").pop();
      return SKIP.has(name) ? null : `${name}[]`;
    }
    return null;
  }
  return null;
}

/** Resolve an OpenAPI parameter schema to a TypeScript type string. */
function paramTsType(schema) {
  if (!schema) return "unknown";
  if (schema.anyOf) {
    const nonNull = schema.anyOf.filter((v) => v.type !== "null");
    const nullable = nonNull.length < schema.anyOf.length;
    const inner = nonNull.map((v) => paramTsType(v)).join(" | ");
    return nullable ? `${inner} | null` : inner;
  }
  if (schema.enum) return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  if (schema.type === "integer" || schema.type === "number") return "number";
  if (schema.type === "boolean") return "boolean";
  if (schema.type === "string") return "string";
  return "unknown";
}

/** Convert a tag slug to a camelCase query key constant name. */
function tagToKeyName(tag) {
  return (
    tag
      .split("-")
      .map((w, i) => (i === 0 ? w : w.charAt(0).toUpperCase() + w.slice(1)))
      .join("") + "Keys"
  );
}
