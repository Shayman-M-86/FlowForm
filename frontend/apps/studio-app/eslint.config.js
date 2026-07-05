import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'src/routeTree.gen.ts', 'src/api/generated/**']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  {
    files: ['src/routes/**/*.{ts,tsx}', 'src/auth/UserContext.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    files: [
      'src/components/CreateProjectForm.tsx',
      'src/components/CreateSurveyForm.tsx',
    ],
    rules: {
      'react-hooks/incompatible-library': 'off',
    },
  },
  {
    files: [
      'src/pages/ProjectDashboardTabPages/SettingsTab.tsx',
      'src/pages/ProjectDashboardTabPages/SurveysTab.tsx',
      'src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts',
    ],
    rules: {
      'react-hooks/set-state-in-effect': 'off',
    },
  },
])
