<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { createConversationRecord } from "../conversations";

const apiClient = createApiClient();
const router = useRouter();

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const draftText = ref(`{
  "trigger": "wake",
  "status": "active",
  "metadata": {}
}`);

async function submit(): Promise<void> {
  submitting.value = true;
  errorMessage.value = null;

  try {
    const created = await createConversationRecord(apiClient, JSON.parse(draftText.value));
    await router.push(`/resources/conversations/${created.id}`);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to create conversation.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="page conversation-create-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Create conversation</p>
        <h2 class="page-hero__title">Start a new conversation</h2>
        <p class="panel-intro">
          Create a conversation record. Messages can be added afterwards.
        </p>
      </div>

      <RouterLink to="/resources/conversations" class="button button--ghost">Back to inbox</RouterLink>
    </header>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="New conversation" title="Conversation data" />

      <label class="form-field form-field--wide">
        <span class="form-label">Conversation data</span>
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </label>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create conversation" }}
        </button>
      </div>
    </article>
  </section>
</template>