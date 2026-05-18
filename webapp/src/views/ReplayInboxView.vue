<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PaginationControls from "../components/PaginationControls.vue";
import { formatDate, formatDuration, replayRaceAbbr, replayRaceClass } from "../formatters";
import { loadReplayInbox } from "../replays";
import type { PaginatedResponse, ReplayRecord } from "../types";

const apiClient = createApiClient();

const inbox = ref<PaginatedResponse<ReplayRecord> | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const filters = reactive({
  player: "",
  map: "",
  sort: "-date",
  currentPage: 1,
  docsPerPage: 25,
});

async function refreshInbox(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    inbox.value = await loadReplayInbox(apiClient, {
      player: filters.player || undefined,
      map: filters.map || undefined,
      sort: filters.sort,
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load replays.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshInbox();
});
</script>

<template>
  <section class="page replay-page">
    <PageHeader eyebrow="Replay review" title="Replays">
      <template #actions>
        <RouterLink to="/resources/replays" class="button button--ghost">
          Maintenance
        </RouterLink>
      </template>
    </PageHeader>

    <section class="panel inbox-pane inbox-pane--filter">
      <PanelHeading eyebrow="Filters" title="Refine list" />

      <div class="inbox-filter-row">
        <FormField label="Player" class="inbox-filter-field">
          <input v-model="filters.player" class="text-input" type="text" placeholder="Name…" @keyup.enter="refreshInbox" />
        </FormField>

        <FormField label="Map" class="inbox-filter-field">
          <input v-model="filters.map" class="text-input" type="text" placeholder="Map name…" @keyup.enter="refreshInbox" />
        </FormField>

        <FormField label="Sort" class="inbox-filter-field inbox-filter-field--narrow">
          <input v-model="filters.sort" class="text-input mono-copy" type="text" />
        </FormField>

        <FormField label="Page" class="inbox-filter-field inbox-filter-field--narrow">
          <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" @keyup.enter="refreshInbox" />
        </FormField>

        <div class="inbox-filter-field inbox-filter-field--action">
          <span class="form-label">&nbsp;</span>
          <button type="button" class="button button--accent" @click="refreshInbox">Apply</button>
        </div>
      </div>
    </section>

    <section class="panel inbox-pane">
      <PanelHeading eyebrow="Results" :title="inbox ? `${inbox.docs_quantity} replays` : 'Replays'">
        <template #aside>
          <span v-if="inbox" class="pill">
            Page {{ inbox.current_page }} of {{ inbox.page_quantity }}
          </span>
        </template>
      </PanelHeading>

      <LoadingErrorEmpty
        :loading="loading"
        :error="errorMessage"
        :empty="!inbox || inbox.docs.length === 0"
        loading-message="Loading…"
        empty-message="No replays matched the current filters."
        loading-class="muted-copy list-block-spacing"
        error-class="muted-copy list-block-spacing error-copy"
        empty-class="muted-copy list-block-spacing"
      >
        <ul class="list list-block-spacing">
          <li
            v-for="replay in inbox?.docs ?? []"
            :key="replay.id"
            class="list-row list-row--linked replay-row"
          >
            <RouterLink :to="`/replays/${replay.id}`" class="list-row__overlay" aria-label="Open replay" />

            <div class="replay-row__main">
              <strong class="replay-row__map">{{ replay.map_name }}</strong>
              <p class="replay-row__matchup">
                <template v-for="(player, idx) in replay.players" :key="player.toon_handle">
                  <span v-if="idx > 0" class="replay-row__vs"> vs </span>
                  <span class="replay-row__player-name" :class="replayRaceClass(player.play_race)">{{ player.name }}</span>
                  <span class="replay-row__race" :class="replayRaceClass(player.play_race)">{{ replayRaceAbbr(player.play_race) }}</span>
                </template>
              </p>
            </div>

            <div class="replay-row__meta">
              <span class="tag">{{ formatDate(replay.date) }}</span>
              <span v-if="replay.real_length" class="tag">{{ formatDuration(replay.real_length) }}</span>
            </div>
          </li>
        </ul>

        <PaginationControls
          :current-page="filters.currentPage"
          :total-pages="inbox?.page_quantity ?? 1"
          @prev="filters.currentPage--; refreshInbox()"
          @next="filters.currentPage++; refreshInbox()"
        />
      </LoadingErrorEmpty>
    </section>
  </section>
</template>

<style scoped>
.replay-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
}

.replay-row__main {
  flex: 1;
  display: grid;
  gap: 4px;
  min-width: 0;
}

.replay-row__map {
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text);
}

.replay-row__matchup {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 3px;
}

.replay-row__vs {
  color: var(--text-muted);
  font-size: 0.8rem;
  padding: 0 2px;
}

.replay-row__player-name.race--t,
.replay-row__race.race--t { color: var(--race-t); }

.replay-row__player-name.race--p,
.replay-row__race.race--p { color: var(--race-p); }

.replay-row__player-name.race--z,
.replay-row__race.race--z { color: var(--race-z); }

.replay-row__player-name.race--r,
.replay-row__race.race--r { color: var(--race-r); }

.replay-row__race {
  font-size: 0.7rem;
  font-family: var(--display);
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 0 3px;
}

.replay-row__id {
  margin: 0;
  font-size: 0.72rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.replay-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex-shrink: 0;
}
</style>
