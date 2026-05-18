<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { createMetadataRecord } from "../metadata";

const apiClient = createApiClient();
const router = useRouter();

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const draftText = ref(`{
  "replay": "",
  "description": "",
  "tags": [],
  "replay_summary_conversation": null
}`);

async function submit(): Promise<void> {
  submitting.value = true;
  errorMessage.value = null;

  try {
    const created = await createMetadataRecord(apiClient, JSON.parse(draftText.value));
    await router.push(`/resources/metadata/${created.id}`);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Unable to create metadata.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="page metadata-create-page">
    <PageHeader
      variant="hero"
      eyebrow="New annotation"
      title="Add a new replay annotation"
      intro="Fill in the annotation details below."
    >
      <template #actions>
        <RouterLink to="/resources/metadata" class="button button--ghost">Back to inbox</RouterLink>
      </template>
    </PageHeader>

    <article class="panel panel-stack">
      <PanelHeading eyebrow="New annotation" title="Annotation data" />

      <FormField class="form-field--wide" label="Annotation data">
        <textarea v-model="draftText" class="text-area" spellcheck="false" />
      </FormField>

      <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

      <div class="button-row">
        <button type="button" class="button button--accent" :disabled="submitting" @click="submit">
          {{ submitting ? "Creating..." : "Create annotation" }}
        </button>
      </div>
    </article>
  </section>
</template>