<script setup>
import { computed } from 'vue';
import SearchHighlight from '../search/SearchHighlight.vue';
import { snippet } from './reader-state.js';
const props = defineProps({ row: Object, t: Object, date: String, query: String, options: Object, isNew: Boolean, newLabel: String });
defineEmits(['open']);
const excerpt = computed(() => snippet(props.row.record, props.query, props.options));
</script>

<template>
  <button class="result-card" type="button" :data-id="row.id" @click="$emit('open', row.id)">
    <span class="card-date">{{ date }}<span v-if="isNew" class="new-badge">{{ newLabel }}</span><svg class="card-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg></span>
    <span class="card-person">{{ t[row.metadata.visionary.value] || t.unknown }}</span>
    <span v-if="row.pendingAttribution" class="pending-label">{{ t.pending }}</span>
    <span v-if="row.metadata.type.source_status === 'source_confirmed' && t.messageTypes[row.metadata.type.value]" class="card-meta">{{ t.messageTypes[row.metadata.type.value] }}</span>
    <span v-if="!row.record" class="card-missing">{{ t.unavailable }}</span>
    <template v-else-if="excerpt">
      <span v-if="excerpt.kind === 'context'" class="snippet-context">{{ t.context }}</span>
      <SearchHighlight class="card-snippet" :text="excerpt.text" :ranges="excerpt.ranges" />
    </template>
    <span v-else class="card-missing">{{ t.noText }}</span>
  </button>
</template>
