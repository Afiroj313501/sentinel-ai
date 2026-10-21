# Sentinel AI frontend

The frontend is a Vite-powered React and TypeScript application. It expects the
backend API to be available at `http://localhost:8000` during local development.

From this directory:

```powershell
npm install
npm run dev
```

The available validation commands are:

```powershell
npm test
npm run build
npm run lint
```

`npm test` runs frontend unit tests with Vitest. They cover the GitHub URL
checker, the diff and snippet parsers, the formatting helpers, and the API
client. There are no component or end-to-end tests, so the UI itself is
checked manually.
`npm run build` type-checks the application and creates the production bundle.
`npm run lint` runs Oxlint with the repository's checked-in configuration.
