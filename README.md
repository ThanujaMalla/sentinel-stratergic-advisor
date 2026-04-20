# Sentinel Frontend

A high-performance React dashboard for strategic intelligence.

## Tech Stack

- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS 4 + custom CSS variables
- **Icons**: Lucide React
- **State Management**: Custom React Hooks (`useDashboard`)
- **Error Handling**: React Error Boundaries

## Project Structure

- `src/components/`: Reusable UI components broken down by dashboard section.
- `src/hooks/`: Custom hooks for data fetching and state management.
- `src/types.ts`: TypeScript interfaces for the dashboard data.
- `src/App.tsx`: Main entry point (refactored for modularity).
- `src/index.css`: Global styles and design system tokens.

## Development

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the dev server:
   ```bash
   npm run dev
   ```

## Build & Production

1. Build for production:
   ```bash
   npm run build
   ```
2. The output will be in the `dist/` directory.
