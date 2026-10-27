import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementIcons from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
Object.entries(ElementIcons).forEach(([name, component]) => app.component(name, component))
app.use(router).use(ElementPlus).mount('#app')
