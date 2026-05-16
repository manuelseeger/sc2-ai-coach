<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { createReplayRecord } from "../replays";

const apiClient = createApiClient();
const router = useRouter();

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const draftText = ref(`{
  "id": "",
  "build": 0,
  "category": "Ladder",
  "date": "2026-01-01T00:00:00Z",
  "expansion": "LotV",
  "filehash": "",
  "filename": "",
  "frames": 0,
  "game_fps": 16,
  "game_length": 0,
  "game_type": "1v1",
  "is_ladder": true,
  "is_private": false,
  "map_name": "",
  "map_size": [0, 0],
  "observers": [],
  "players": [],
  "region": "eu",
  "release": "",
  "real_length": 0,
  "real_type": "1v1",
  "release_string": "",
  "speed": "Faster",
  "stats": {
    "loserDoesGG": false
  },
  "time_zone": 0,
  "type": "1v1",
  "unix_timestamp": 0,
  "versions": []
}`);

async function submit(): Promise<void> {
  submitting.value = true;
  errorMessage.value = null;

  try {
    const created = await createReplayRecord(apiClient, JSON.parse(draftText.value));
    await router.push(`/resources/replays/${created.id}`);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to create replay.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="page replay-create-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Create replay</p>
        <h2 class="page-hero__title">Open a new replay document through the generic editor</h2>
        <p class="panel-intro">
          Replay creation stays in the generic maintenance surface, separate from the curated
          replay-review route.
        </p>
      </div>

      <RouterLink to="/resources/replays" class="button button--ghost">Back to replay maintenance</RouterLink>
    </header>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="Create body" title="Replay JSON" />

      <label class="form-field form-field--wide">
        <span class="form-label">Request JSON</span>
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </label>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create replay" }}
        </button>
      </div>
    </article>
  </section>
</template>