const minimo = { statements: 70, branches: 70, functions: 70, lines: 70 };

module.exports = {
  testEnvironment: 'jsdom',
  globals: { __API_URL__: 'http://localhost:8000' },
  testMatch: ['<rootDir>/tests/**/*.test.[jt]s?(x)'],
  transform: { '^.+\\.[jt]sx?$': 'babel-jest' },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  moduleNameMapper: { '\\.(css|less|scss)$': '<rootDir>/tests/styleMock.cjs' },
  clearMocks: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/main.jsx',
  ],
  coverageDirectory: 'qa-results/coverage',
  coverageReporters: ['text', 'html', 'lcov', 'json-summary'],
  coverageThreshold: {
    global: minimo,
    './src/App.jsx': minimo,
    './src/Reporte.jsx': minimo,
    './src/verLogs.jsx': minimo,
    './src/servicios/analisis.js': minimo,
    './src/componentes/ResultadoRevision.jsx': minimo,
  },
};
