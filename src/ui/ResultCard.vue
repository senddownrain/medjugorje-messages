<script setup>
import { computed } from 'vue';
import SearchHighlight from '../search/SearchHighlight.vue';
import { snippet } from './reader-state.js';
const props = defineProps({ row: Object, t: Object, date: String, query: String, options: Object });
defineEmits(['open']);
const excerpt = computed(() => snippet(props.row.record, props.query, props.options));
</script>

<template>
  <button class="result-card" type="button" :data-id="row.id" @click="$emit('open', row.id)">
    <span class="card-date">{{ date }}<svg class="card-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg></span>
    <span class="card-person">{{ t[row.metadata.visionary.value] || t.unknown }}</span>
    <span v-if="row.pendingAttribution" class="pending-label">{{ t.pending }}</span>
    <span class="card-meta">{{ t[row.metadata.type.value] }} · {{ t[row.metadata.series.value] || t.seriesUnknown }}</span>
    <span v-if="!row.record" class="card-missing">{{ t.unavailable }}</span>
    <template v-else-if="excerpt">
      <span v-if="excerpt.kind === 'context'" class="snippet-context">{{ t.context }}</span>
      <SearchHighlight class="card-snippet" :text="excerpt.text" :ranges="excerpt.ranges" />
    </template>
    <span v-else class="card-missing">{{ t.noText }}</span>
  </button>
</template>
