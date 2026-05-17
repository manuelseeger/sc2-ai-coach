<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { createPlayerRecord } from "../players";

const apiClient = createApiClient();
const router = useRouter();

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const draftText = ref(`{
  "id": "2-S2-1-123456",
  "toon_handle": "2-S2-1-123456",
  "name": "KnownOpponent",
  "aliases": [],
  "tags": []
}`);

async function submit(): Promise<void> {
  submitting.value = true;
  errorMessage.value = null;

  try {
    const created = await createPlayerRecord(apiClient, JSON.parse(draftText.value));
    await router.push(`/resources/players/${created.toon_handle}`);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to create player.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="page player-create-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Create player</p>
        <h2 class="page-hero__title">Open a new player identity record</h2>
        <p class="panel-intro">
          Submit a valid player document, then continue in the detail screen for patch, replace,
          or delete work.
        </p>
      </div>

      <RouterLink to="/resources/players" class="button button--ghost">Back to inbox</RouterLink>
    </header>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="Create body" title="Player JSON" />

      <label class="form-field form-field--wide">
        <span class="form-label">Request JSON</span>
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </label>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create player" }}
        </button>
      </div>
    </article>
  </section>
</template>