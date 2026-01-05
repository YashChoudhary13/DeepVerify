/* types */export interface ModelResult {
  model_name: string;
  score: number;
  version?: string;
  heatmap_url?: string;
  image_url?: string;
  run_time_ms?: number;
  labels?: any;
}

export interface Consensus {
  score: number;
  decision: string;
  explanation?: string[];
}

export interface JobResponse {
  job_id: string;
  status: string;
  created_at: string;
  image?: {
    thumbnail_url?: string;
  };
  consensus?: Consensus;
  models: ModelResult[];
}

export interface DashboardJob {
  job_id: string;
  analysis_number?: number;
  display_name?: string;
  created_at: string;
  image?: {
    thumbnail_url?: string;
  };
  consensus?: {
    score: number;
    decision: string;
  };
}
