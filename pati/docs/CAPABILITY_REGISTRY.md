# CAPABILITY_REGISTRY.md

Source of truth: `pati_api/registries.py` (code catalog) merged with DB
overrides (`registered_capabilities`). Exposed at `GET /api/v1/capabilities`
and validated against `schemas/capability.schema.json`.

## Fields

`capability_id`, `category`, `description`, `risky`,
`min_autonomy_level` (0-6, see docs/AUTONOMY.md), `worker_types`.

## Coverage (94 entries)

- **text**: text_generation, reasoning, summarization, translation,
  structured_output, classification, extraction, rewriting,
  question_answering
- **coding**: coding, code_generation, code_review, debugging, refactoring,
  repository_analysis, coding_agent, test_generation,
  documentation_generation, architecture_generation
- **research**: web_research, document_research, source_comparison,
  fact_checking, literature_research, market_research, technical_research,
  research_synthesis
- **vision**: vision, image_understanding, OCR, document_vision,
  image_captioning, visual_question_answering
- **image**: image_generation, image_editing, image_to_image,
  image_upscaling, background_removal, character_generation,
  character_consistency
- **video**: text_to_video, image_to_video, video_to_video,
  video_upscaling, frame_interpolation, video_editing,
  storyboard_generation, scene_generation, character_consistency_video
- **audio**: text_to_speech, speech_to_text, voice_conversion,
  voice_generation, lip_sync, music_generation, audio_processing
- **automation**: browser_automation, web_scraping, filesystem_operations,
  git_operations, github_operations, API_operations, scheduled_tasks
- **app**: app_generation, frontend_generation, backend_generation,
  database_generation, testing, browser_testing, deployment, CI_CD,
  security_scanning
- **infrastructure**: container_execution, GPU_execution, batch_execution,
  remote_execution, artifact_storage, benchmarking, model_evaluation,
  tool_evaluation
- **local_fs** (Local Agent enforced): filesystem_read/create/modify/copy/
  move/delete/list, filesystem_organize, artifact_save_local,
  report_generation, run_scripts, run_commands, run_local_models,
  system_inspection

## Routing contract

The router matches a stage's `capability` against each worker's declared
capabilities. Worker-type affinity (`worker_types`) is advisory metadata;
the live match is capability-based, so a Kaggle worker and a future local
GPU can both serve `image_generation` and the router scores between them.

## Extension

Register new capabilities via DB insert (admin tooling) or extend the code
catalog in a PR — both are merged reads; nothing hard-codes a provider.
