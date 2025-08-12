# TODO - Future Enhancements

## Conversation Tracking Across Resume Sessions

**Problem**: When closing and resuming Claude Code conversations, each resume creates a new session in the logs, making it difficult to track work that spans multiple sessions.

**Solution**: Add conversation-level tracking that links related sessions together.

### Implementation Ideas

1. **Database Schema Enhancement**
   - Add `conversation_id` field to sessions table
   - Link sessions based on:
     - Same project directory
     - Resume source indicator
     - Transcript path pattern
     - Time proximity (sessions within X hours)

2. **New Tool: `track_conversation.py`**
   ```bash
   # View current conversation across all resumes
   python3 tools/track_conversation.py --current
   
   # List all conversations in project
   python3 tools/track_conversation.py --list
   
   # Show specific conversation timeline
   python3 tools/track_conversation.py --id <conversation_id>
   ```

3. **Enhanced Analytics**
   - Update `analyze_workflow.py` to support `--conversation` flag
   - Show aggregated stats across entire conversations
   - Track patterns that span multiple work sessions
   - Total time spent on a conversation thread

4. **Query Improvements**
   - Add to `query_logs.py`:
     - `--group-by-conversation` flag
     - `--conversation <id>` to filter by conversation
   - Show both session-level and conversation-level views

### Technical Details

- Sessions with `"source": "resume"` in metadata are continuations
- Use transcript_path to definitively link related sessions
- Consider creating a conversations table for metadata
- Could analyze transcript files for even deeper linking

### Benefits

- Track total time spent on a feature/bug across multiple days
- See agent usage patterns for entire workflows
- Better understand how work progresses across sessions
- More accurate time tracking for project management

---

## Other Future Ideas

(Add new enhancement ideas here as they arise)