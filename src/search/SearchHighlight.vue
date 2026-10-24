<script setup>
import { computed } from 'vue';
import { highlightParts } from './unicode.js';
const props = defineProps({ text: { type: String, required: true }, ranges: { type: Array, default: () => [] } });
const parts = computed(() => highlightParts(props.text, props.ranges));
</script>

<template>
  <span><template v-for="(part, n) in parts" :key="n"><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></span>
</template>
