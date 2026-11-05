import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'
import '@/styles/globals.css'
import App from './App'
import { IS_MOCK } from './lib/config'
import { createLiveDemoController, registerDemoController } from './lib/demo'
import { startMocks } from './mocks/browser'

async function prepare() {
  if (IS_MOCK) {
    await startMocks()
  } else {
    registerDemoController(createLiveDemoController())
  }
}

prepare()
  .then(() => {
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
  .catch((err) => {
    console.error('Failed to start application:', err)
  })
