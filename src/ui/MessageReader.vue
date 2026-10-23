<script setup>
import BrandMark from './BrandMark.vue';
defineProps({ row: Object, record: Object, t: Object, date: String, latest: Boolean,
  language: String, languages: Array, archiveLoaded: Boolean });
defineEmits(['language']);
</script>

<template>
  <article class="reading" :data-message-id="row.id">
    <p class="reading-kicker"><BrandMark /> {{ latest ? t.latestMessage : t[row.type.value] }}</p>
    <h1>{{ date }}</h1>
    <p class="reading-person">{{ t[row.visionary.value] || t.unknown }}</p>
    <p v-if="row.visionary.editorial_status === 'pending'" class="pending-label">{{ t.pending }}</p>
    <p class="reading-series">{{ t[row.type.value] }} · {{ t[row.series.value] || t.seriesUnknown }}</p>
    <div class="reading-divider" aria-hidden="true">✧</div>
    <div :lang="language" class="message-body">
      <p v-if="!record" class="empty-text">{{ archiveLoaded ? t.unavailable : t.awaiting }}</p>
      <p v-else-if="!record.text" class="empty-text">{{ t.noText }}</p>
      <template v-if="record?.segments?.length">
        <template v-for="(segment, n) in record.segments" :key="n">
          <p v-if="segment.kind === 'message'" class="message-text">{{ segment.text }}</p>
          <aside v-else class="context-text"><span>{{ t.note }}</span>{{ segment.text }}</aside>
        </template>
      </template>
      <p v-else-if="record?.text" class="message-text">{{ record.text }}</p>
    </div>
    <div class="other-languages" v-if="languages.length">
      <span>{{ t.available }}</span>
      <div><button v-for="item in languages" :key="item.code" type="button"
        :aria-pressed="language === item.code" @click="$emit('language', item.code)">{{ item.code.toUpperCase() }}</button></div>
    </div>
    <a v-if="record?.source_url" class="source-link" :href="record.source_url" target="_blank" rel="noopener noreferrer">{{ t.original }} ↗</a>
  </article>
</template>
