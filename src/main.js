import { createApp } from 'vue';
import App from './App.vue';
import { createVuetify } from 'vuetify';
import { VApp, VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSelect } from 'vuetify/components';
import 'vuetify/styles';
import './style.css';
import { registerSW } from 'virtual:pwa-register';

const vuetify = createVuetify({
  components: { VApp, VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSelect },
  theme: {
    defaultTheme: 'marianLight',
    themes: {
      marianLight: {
        dark: false,
        colors: {
          background: '#f8f9fa', surface: '#fffefa', primary: '#6f8eaa',
          secondary: '#b69b6c', 'on-background': '#293746', 'on-surface': '#293746'
        }
      },
      marianDark: {
        dark: true,
        colors: {
          background: '#151c24', surface: '#202a35', primary: '#a5c9e9',
          secondary: '#d5bc86', 'on-background': '#eaf0f5', 'on-surface': '#eaf0f5'
        }
      }
    }
  }
});
registerSW({ immediate: true });
createApp(App).use(vuetify).mount('#app');
