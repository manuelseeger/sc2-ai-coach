<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import PageHeader from "../components/PageHeader.vue";
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
    <PageHeader
      variant="hero"
      eyebrow="Create replay"
      title="Add a new replay manually"
      intro="Enter the replay data below. Required fields must be valid before saving."
    >
      <template #actions>
        <RouterLink to="/resources/replays" class="button button--ghost">Back to replays</RouterLink>
      </template>
    </PageHeader>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="New replay" title="Replay data" />

      <FormField class="form-field--wide" label="Replay data">
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </FormField>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create replay" }}
        </button>
      </div>
    </article>
  </section>
</template>