<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PaginationControls from "../components/PaginationControls.vue";
import { loadPlayerInbox, loadPlayerPortraitMetadataMap } from "../players";
import type { PaginatedResponse, PlayerInfoRecord, PlayerPortraitMetadataRecord } from "../types";

const apiClient = createApiClient();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const inbox = ref<PaginatedResponse<PlayerInfoRecord> | null>(null);
const portraits = ref<Record<string, PlayerPortraitMetadataRecord>>({});

const filters = reactive({
  q: "",
  tag: "",
  sort: "name",
  currentPage: 1,
});

async function refreshInbox(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    const loaded = await loadPlayerInbox(apiClient, {
      q: filters.q || undefined,
      tag: filters.tag || undefined,
      sort: filters.sort || undefined,
      current_page: filters.currentPage,
      docs_per_page: 25,
    });
    inbox.value = loaded;
    portraits.value = await loadPlayerPortraitMetadataMap(
      apiClient,
      loaded.docs.map((player) => player.toon_handle),
    );
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load players.";
    inbox.value = null;
    portraits.value = {};
  } finally {
    loading.value = false;
  }
}

function primaryPortraitUrl(player: PlayerInfoRecord): string | null {
  const metadata = portraits.value[player.toon_handle];
  if (!metadata) return null;
  if (metadata.portrait.available) return metadata.portrait.url;
  if (metadata.portrait_constructed.available) return metadata.portrait_constructed.url;
  return null;
}

onMounted(async () => {
  await refreshInbox();
});
</script>

<template>
  <section class="page players-page">
    <PageHeader eyebrow="Player review" title="Players">
      <template #actions>
        <RouterLink to="/resources/players" class="button button--ghost">Maintenance</RouterLink>
      </template>
    </PageHeader>

    <section class="panel inbox-pane inbox-pane--filter">
      <PanelHeading eyebrow="Filters" title="Refine list" />

      <div class="inbox-filter-row">
        <FormField label="Search" class="inbox-filter-field">
          <input v-model="filters.q" class="text-input" type="text" placeholder="Name, alias, or toon handle" @keyup.enter="refreshInbox" />
        </FormField>

        <FormField label="Tag" class="inbox-filter-field">
          <input v-model="filters.tag" class="text-input" type="text" placeholder="ladder" @keyup.enter="refreshInbox" />
        </FormField>

        <FormField label="Sort" class="inbox-filter-field inbox-filter-field--narrow">
          <input v-model="filters.sort" class="text-input mono-copy" type="text" @keyup.enter="refreshInbox" />
        </FormField>

        <FormField label="Page" class="inbox-filter-field inbox-filter-field--narrow">
          <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" @keyup.enter="refreshInbox" />
        </FormField>

        <div class="inbox-filter-field inbox-filter-field--action">
          <span class="form-label">&nbsp;</span>
          <div class="inbox-filter-actions">
            <button type="button" class="button button--accent" @click="refreshInbox">Apply</button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel inbox-pane">
      <PanelHeading eyebrow="Results" :title="inbox ? `${inbox.docs_quantity} players` : 'Players'">
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
        loading-message="Loading players..."
        empty-message="No players matched the current filters."
      >
        <ul class="list list-block-spacing">
          <li v-for="player in inbox?.docs ?? []" :key="player.toon_handle" class="list-row list-row--linked player-review-row">
            <RouterLink :to="`/players/${player.toon_handle}`" class="list-row__overlay" :aria-label="`Open ${player.name}`" />

            <div class="player-review-row__portrait">
              <img v-if="primaryPortraitUrl(player)" :src="primaryPortraitUrl(player) ?? ''" :alt="`${player.name} portrait`" class="player-review-row__image" />
              <div v-else class="player-review-row__fallback">No portrait</div>
            </div>

            <div class="player-review-row__body">
              <div class="split-topline">
                <div>
                  <strong>{{ player.name }}</strong>
                  <p class="player-review-row__meta mono-copy">{{ player.toon_handle }}</p>
                </div>
                <div class="tag-row">
                  <span class="tag">{{ player.aliases.length }} aliases</span>
                  <span class="tag">{{ player.tags?.length ?? 0 }} tags</span>
                </div>
              </div>

              <div v-if="player.aliases.length" class="tag-row">
                <span v-for="alias in player.aliases.slice(0, 3)" :key="alias.name" class="tag">{{ alias.name }}</span>
              </div>

              <div class="button-row">
                <RouterLink :to="`/resources/players/${player.toon_handle}`" class="button button--ghost row-action">
                  Maintenance
                </RouterLink>
              </div>
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
.player-review-row {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 18px;
  align-items: center;
  padding: 16px 20px;
}

.player-review-row__portrait {
  width: 92px;
  height: 92px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(16, 24, 38, 0.9), rgba(10, 16, 26, 1));
}

.player-review-row__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.player-review-row__fallback {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  font-size: 0.75rem;
  text-align: center;
}

.player-review-row__body {
  display: grid;
  gap: 10px;
}

.player-review-row__meta {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 0.78rem;
}

@media (max-width: 700px) {
  .player-review-row {
    grid-template-columns: 1fr;
  }

  .player-review-row__portrait {
    width: 100%;
    max-width: 140px;
    height: 140px;
  }
}
</style>