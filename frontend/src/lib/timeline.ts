/**
 * Timeline model for merging conversation messages and workflow executions
 * into one chronological chat view.
 *
 * Every item has a stable `id` for deduplication and a `sortKey` (ISO string)
 * used for chronological ordering.
 */

export interface TimelineMessage {
  kind: 'message';
  id: string;
  sortKey: string;
  role: 'user' | 'assistant';
  content: string;
  type?: string;
  workflowId?: string;
  executionId?: string;
}

export interface TimelineWorkflow {
  kind: 'workflow';
  id: string;
  sortKey: string;
  executionId: string;
  workflowId: string;
  conversationId: string;
  title: string;
  description: string;
  status: string;
  displayStatus: string;
  steps: any[];
  currentStepIndex: number;
  totalSteps: number;
  startedAt: string | null;
  completedAt: string | null;
  stoppedAt: string | null;
  errorMessage: string | null;
  result: string | null;
  resultType: string | null;
  lastCompletedStep: string | null;
  partialResult: string | null;
}

export type TimelineItem = TimelineMessage | TimelineWorkflow;

const DISPLAY_STATUS_MAP: Record<string, string> = {
  Completed: 'completed',
  completed: 'completed',
  Failed: 'stopped',
  failed: 'stopped',
  Cancelled: 'stopped',
  cancelled: 'stopped',
  Executing: 'running',
  executing: 'running',
  Planning: 'running',
  planning: 'running',
  Waiting: 'running',
  waiting: 'running',
  Retry: 'running',
  retry: 'running',
  Stopping: 'running',
  stopping: 'running',
  Idle: 'draft',
  idle: 'draft',
};

export function mapDisplayStatus(status: string): string {
  return DISPLAY_STATUS_MAP[status] || 'draft';
}

/** Stable dedup key for a chat message. */
function messageDedupeKey(msg: any): string {
  return msg._id || msg.execution_id || `${msg.created_at}-${msg.content?.substring(0, 40)}`;
}

/** Stable dedup key for a workflow execution. */
function workflowDedupeKey(exec: any): string {
  return exec._id;
}

/**
 * Merge conversation messages and workflow executions into a single
 * chronological timeline, deduplicating by stable IDs.
 *
 * Rules:
 *  - Messages are sorted by created_at
 *  - Workflows are sorted by started_at
 *  - If a chat message has execution_id matching a workflow execution,
 *    AND it is a terminal-state message (workflow_state in metadata),
 *    it is deduplicated away (the workflow item provides the same info).
 *  - If a chat message has execution_id but is NOT a terminal-state message
 *    (e.g. workflow_plan), it stays in the timeline.
 *  - Active (non-terminal) workflows are merged at their started_at position.
 */
export function mergeTimeline(
  messages: any[],
  workflows: any[],
): TimelineItem[] {
  const items: TimelineItem[] = [];

  // Index workflows by execution_id for dedup checks
  const workflowExecIds = new Set<string>();
  for (const wf of workflows) {
    workflowExecIds.add(wf._id);
  }

  // Process messages
  for (const msg of messages) {
    const execId = msg.execution_id;
    const metadata = msg.metadata || {};
    const workflowState = metadata.workflow_state;

    // If this message is a terminal-state duplicate of a workflow execution, skip it
    if (execId && workflowExecIds.has(execId) && workflowState) {
      continue;
    }

    const sortKey = msg.created_at || '';
    items.push({
      kind: 'message',
      id: messageDedupeKey(msg),
      sortKey,
      role: msg.role || 'assistant',
      content: msg.content || '',
      type: msg.message_type,
      workflowId: msg.workflow_id,
      executionId: execId,
    });
  }

  // Process workflows
  for (const wf of workflows) {
    const sortKey = wf.started_at || wf.completed_at || wf.stopped_at || '';
    items.push({
      kind: 'workflow',
      id: workflowDedupeKey(wf),
      sortKey,
      executionId: wf._id,
      workflowId: wf.workflow_id || '',
      conversationId: wf.conversation_id || '',
      title: wf.title || '',
      description: wf.description || '',
      status: wf.status || 'Unknown',
      displayStatus: mapDisplayStatus(wf.status || ''),
      steps: wf.steps || [],
      currentStepIndex: wf.current_step_index || 0,
      totalSteps: wf.total_steps || 0,
      startedAt: wf.started_at || null,
      completedAt: wf.completed_at || null,
      stoppedAt: wf.stopped_at || null,
      errorMessage: wf.error_message || null,
      result: wf.result || null,
      resultType: wf.result_type || null,
      lastCompletedStep: wf.last_completed_step || null,
      partialResult: wf.partial_result || null,
    });
  }

  // Sort chronologically by sortKey
  items.sort((a, b) => {
    if (a.sortKey < b.sortKey) return -1;
    if (a.sortKey > b.sortKey) return 1;
    // Stable tiebreak: workflows after messages at same timestamp
    if (a.kind === 'message' && b.kind === 'workflow') return -1;
    if (a.kind === 'workflow' && b.kind === 'message') return 1;
    return 0;
  });

  return items;
}
