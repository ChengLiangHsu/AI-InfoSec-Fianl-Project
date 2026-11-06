import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { initializeVisitor } from './lib/visitorSession'

async function startApp() {
  await initializeVisitor()
  createApp(App).mount('#app')
}

startApp().catch(() => {
  const root = document.getElementById('app')
  if (root) root.textContent = '暫時無法連線，請稍後重新整理頁面。'
})
