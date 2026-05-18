<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import PageHeader from "../components/PageHeader.vue";
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
    <PageHeader
      variant="hero"
      eyebrow="Create conversation"
      title="Start a new conversation"
      intro="Create a conversation record. Messages can be added afterwards."
    >
      <template #actions>
        <RouterLink to="/resources/conversations" class="button button--ghost">Back to inbox</RouterLink>
      </template>
    </PageHeader>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="New conversation" title="Conversation data" />

      <FormField class="form-field--wide" label="Conversation data">
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </FormField>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create conversation" }}
        </button>
      </div>
    </article>
  </section>
</template>