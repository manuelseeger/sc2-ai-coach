<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import PageHeader from "../components/PageHeader.vue";
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
    <PageHeader
      variant="hero"
      eyebrow="Create player"
      title="Add a new player"
      intro="Fill in the player details below."
    >
      <template #actions>
        <RouterLink to="/resources/players" class="button button--ghost">Back to inbox</RouterLink>
      </template>
    </PageHeader>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="New player" title="Player data" />

      <FormField class="form-field--wide" label="Player data">
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </FormField>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create player" }}
        </button>
      </div>
    </article>
  </section>
</template>