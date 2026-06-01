/**
 * Generates from backend/openapi.yaml:
 *
 *   apps/studio-app/src/api/generated/rbac.gen.ts
 *     — FlowFormPermission union + operationPermissions map + routePermissions array
 *
 *   packages/schema/src/generated/constraints.gen.ts
 *     — TypeScript interfaces + *Constraints objects (runtime constraint metadata for UI)
 *
 * The openapi-typescript schema (schema.ts) is generated separately via openapi:types.
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
const schemaPackageDir = resolve(
  __dirname,
  "../packages/schema/src/generated",
);

mkdirSync(schemaPackageDir, { recursive: true });

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

// ─── packages/schema/src/generated/builder.gen.ts ────────────────────────
// Interfaces for schemas marked x-flowform-export: builder, plus all their
// transitive $ref dependencies.

// Collect entry points — schemas with x-flowform-export: builder
const builderEntryPoints = new Set(
  Object.entries(allSchemas)
    .filter(([, schema]) => schema["x-flowform-export"] === "builder")
    .map(([name]) => name),
);

// Walk refs transitively from all entry points
function collectTransitiveDeps(names, allSchemas) {
  const collected = new Set();
  function visit(name) {
    if (collected.has(name) || !allSchemas[name]) return;
    collected.add(name);
    for (const ref of refsInSchema(allSchemas[name])) visit(ref);
  }
  for (const name of names) visit(name);
  return collected;
}

const builderSchemas = collectTransitiveDeps(builderEntryPoints, allSchemas);
const builderSorted = sorted.filter(([name]) => builderSchemas.has(name));

const interfaceLines = [
  "// This file is auto-generated — do not edit manually",
  "",
];

for (const category of ["subtype", "request", "response"]) {
  const subset = builderSorted.filter(([name]) => schemaCategory(name) === category);
  if (subset.length === 0) continue;

  interfaceLines.push(`// ${"─".repeat(74)}`);
  interfaceLines.push(`// ${category.charAt(0).toUpperCase() + category.slice(1)}s`);
  interfaceLines.push(`// ${"─".repeat(74)}`);
  interfaceLines.push("");

  for (const [name, schema] of subset) {
    if (!schema.properties && (schema.oneOf || schema.anyOf)) {
      const variants = (schema.oneOf ?? schema.anyOf)
        .map((v) => v.$ref ? v.$ref.split("/").pop() : resolveType(v, allSchemas))
        .join(" | ");
      interfaceLines.push(`export type ${name} = ${variants};`);
      interfaceLines.push("");
      continue;
    }

    const props = schema.properties ?? {};
    const required = new Set(schema.required ?? []);

    interfaceLines.push(`export interface ${name} {`);
    for (const [field, def] of Object.entries(props)) {
      interfaceLines.push(`  ${field}${required.has(field) ? "" : "?"}: ${resolveType(def, allSchemas)};`);
    }
    interfaceLines.push(`}`);
    interfaceLines.push("");
  }
}

writeFileSync(`${schemaPackageDir}/builder.gen.ts`, interfaceLines.join("\n"));
console.log(`Generated ${schemaPackageDir}/builder.gen.ts`);

// ─── packages/schema/src/generated/constraints.gen.ts ────────────────────────
// ─── packages/schema/src/generated/builder-constraints.gen.ts ────────────────
// Runtime constraint objects (*Constraints). Full set and builder-scoped set.

function buildConstraintFileLines(entries) {
  const lines = ["// This file is auto-generated — do not edit manually", ""];
  for (const category of ["subtype", "request", "response"]) {
    const subset = entries.filter(([name]) => schemaCategory(name) === category);
    if (subset.length === 0) continue;
    const categoryHasConstraints = subset.some(([, schema]) => {
      return Object.keys(buildConstraints(schema.properties ?? {})).length > 0;
    });
    if (!categoryHasConstraints) continue;
    lines.push(`// ${"─".repeat(74)}`);
    lines.push(`// ${category.charAt(0).toUpperCase() + category.slice(1)}s`);
    lines.push(`// ${"─".repeat(74)}`);
    lines.push("");
    for (const [name, schema] of subset) {
      if (!schema.properties) continue;
      const constraints = buildConstraints(schema.properties);
      if (Object.keys(constraints).length === 0) continue;
      lines.push(`export const ${name}Constraints = {`);
      for (const [field, c] of Object.entries(constraints)) {
        const entries = Object.entries(c)
          .map(([k, v]) => `${k}: ${k === "pattern" ? `/${v}/` : JSON.stringify(v)}`)
          .join(", ");
        lines.push(`  ${field}: { ${entries} },`);
      }
      lines.push(`} as const;`);
      lines.push("");
    }
  }
  return lines;
}

writeFileSync(`${schemaPackageDir}/constraints.gen.ts`, buildConstraintFileLines(sorted).join("\n"));
console.log(`Generated ${schemaPackageDir}/constraints.gen.ts`);

const builderSortedForConstraints = sorted.filter(([name]) => builderSchemas.has(name));
writeFileSync(`${schemaPackageDir}/builder-constraints.gen.ts`, buildConstraintFileLines(builderSortedForConstraints).join("\n"));
console.log(`Generated ${schemaPackageDir}/builder-constraints.gen.ts`);

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
const routePermissionEntries = [];
for (const [path, methods] of Object.entries(spec.paths ?? {})) {
  for (const [method, op] of Object.entries(methods)) {
    const permission = op["x-flowform-rbac"]?.permission ?? null;
    if (!permission) continue;
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
