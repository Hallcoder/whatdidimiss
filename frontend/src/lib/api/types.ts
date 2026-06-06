// Auth
export interface AuthURLResponse {
  auth_url: string;
  state: string;
}

export interface ChannelSummary {
  id: string;
  youtube_channel_id: string;
  channel_title: string | null;
  subscriber_count: number | null;
}

export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  channel: ChannelSummary | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// Video
export interface VideoAnalyzeResponse {
  video_id: string;
  status: string;
  status_url: string;
}

export interface VideoSummary {
  id: string;
  youtube_video_id: string;
  title: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  processing_status: string;
  video_score: number | null;
  created_at: string;
}

export interface VideoDetailResponse {
  id: string;
  youtube_video_id: string;
  title: string | null;
  description: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  processing_status: string;
  processing_error: string | null;
  created_at: string;
}

export interface VideoStatusResponse {
  status: string;
  progress_pct: number;
  current_step: string;
  steps_completed: string[];
  steps_remaining: string[];
  error: string | null;
}

export interface VideoUploadResponse {
  video_id: string;
  status: string;
  status_url: string;
}

export interface ChannelVideoItem {
  youtube_video_id: string;
  title: string;
  thumbnail_url: string | null;
  duration_seconds: number;
  published_at: string;
  view_count: number | null;
  already_analyzed: boolean;
}

export interface ChannelVideosResponse {
  items: ChannelVideoItem[];
  next_page_token: string | null;
  total_results: number | null;
}

// Common
export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

// Dashboard
export interface InsightSummary {
  id: string;
  type: string;
  category: string | null;
  title: string;
  description: string;
  priority_rank: number | null;
  confidence: number | null;
  creator_match: string | null;
  creator_match_note: string | null;
}

export interface SelfAssessmentData {
  hook_score: number | null;
  structure_score: number | null;
  clarity_score: number | null;
  cta_score: number | null;
  energy_score: number | null;
  pacing_score: number | null;
  visual_score: number | null;
  best_part: string | null;
  would_change: string | null;
  submitted_at: string | null;
}

export interface SegmentBrief {
  segment_index: number;
  start_ms: number;
  end_ms: number;
  segment_type: string | null;
  avg_retention: number | null;
}

export interface EngagementSummary {
  views: number | null;
  avg_retention_pct: number | null;
  best_segment: SegmentBrief | null;
  worst_segment: SegmentBrief | null;
}

export interface DashboardResponse {
  video: {
    id: string;
    youtube_video_id: string;
    title: string | null;
    thumbnail_url: string | null;
    duration_seconds: number | null;
    video_score: number | null;
  };
  top_wins: InsightSummary[];
  top_improvements: InsightSummary[];
  next_post_ideas: InsightSummary[];
  creative_tweaks: InsightSummary[];
  engagement_summary: EngagementSummary;
  processing_status: string;
}

// Engagement
export interface RetentionPoint {
  position_ratio: number;
  timestamp_ms: number;
  watch_ratio: number | null;
  relative_performance: number | null;
}

export interface EngagementOverview {
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  avg_view_duration_seconds: number | null;
  avg_view_percentage: number | null;
}

export interface EngagementResponse {
  overview: EngagementOverview;
  retention_curve: RetentionPoint[];
  traffic_sources: Record<string, number> | null;
  demographics: Record<string, Record<string, number>> | null;
}

// Analysis
export interface SegmentDetail {
  id: string;
  segment_index: number;
  start_ms: number;
  end_ms: number;
  segment_type: string | null;
  labels: string[] | null;
  pacing_score: number | null;
}

export interface AnalysisResponse {
  segments: SegmentDetail[];
  shot_count: number;
  avg_pacing: number;
  detected_labels: string[];
  transcript_available: boolean;
}

export interface TranscriptSegment {
  text: string;
  confidence: number;
  start_ms: number;
  end_ms: number;
}

// Insights
export interface ReferencedSegment {
  segment_id: string;
  start_ms: number;
  end_ms: number;
  transcript_snippet: string | null;
}

export interface InsightDetail extends InsightSummary {
  referenced_segments: ReferencedSegment[];
}

export interface InsightsResponse {
  items: InsightDetail[];
}

// Engagement Segments
export interface EngagementSegment {
  segment_id: string;
  segment_index: number;
  start_ms: number;
  end_ms: number;
  segment_type: string | null;
  avg_retention: number | null;
  retention_delta: number | null;
  engagement_label: string | null;
}
