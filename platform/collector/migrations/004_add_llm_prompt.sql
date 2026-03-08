-- Add llm_prompt column to store the full LLM prompt for agent visibility
ALTER TABLE event_logs ADD COLUMN IF NOT EXISTS llm_prompt TEXT NOT NULL DEFAULT '';
