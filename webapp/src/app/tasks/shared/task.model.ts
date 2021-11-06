import { ResponseMessage } from '../../shared/api.models';
import {
  DeleteStrategy,
  QualityNumber,
} from '../../settings/shared/setting.model';

export interface TaskData {
  user_info: Readonly<UserInfo>;
  room_info: Readonly<RoomInfo>;
  task_status: Readonly<TaskStatus>;
}

export enum DataSelection {
  ALL = 'all',

  // live status
  PREPARING = 'preparing',
  LIVING = 'living',
  ROUNDING = 'rounding',

  // task status
  MONITOR_ENABLED = 'monitor_enabled',
  MONITOR_DISABLED = 'monitor_disabled',
  RECORDER_ENABLED = 'recorder_enabled',
  RECORDER_DISABLED = 'recorder_disabled',

  // task running status
  STOPPED = 'stopped',
  WAITTING = 'waitting',
  RECORDING = 'recording',
  REMUXING = 'remuxing',
  INJECTING = 'injecting',
}

export interface UserInfo {
  readonly name: string;
  readonly gender: string;
  readonly face: string;
  readonly uid: number;
  readonly level: number;
  readonly sign: string;
}

export interface RoomInfo {
  readonly uid: number;
  readonly room_id: number;
  readonly short_room_id: number;
  readonly area_id: number;
  readonly area_name: string;
  readonly parent_area_id: number;
  readonly parent_area_name: string;
  readonly live_status: number;
  readonly live_start_time: number;
  readonly online: number;
  readonly title: string;
  readonly cover: string;
  readonly tags: string;
  readonly description: string;
}

export enum RunningStatus {
  STOPPED = 'stopped',
  WAITING = 'waiting',
  RECORDING = 'recording',
  REMUXING = 'remuxing',
  INJECTING = 'injecting',
}

export enum PostprocessorStatus {
  WAITING = 'waiting',
  REMUXING = 'remuxing',
  INJECTING = 'injecting',
}

export interface Progress {
  time: number;
  duration: number;
}

export interface TaskStatus {
  readonly monitor_enabled: boolean;
  readonly recorder_enabled: boolean;
  readonly running_status: RunningStatus;
  readonly elapsed: number;
  readonly data_count: number;
  readonly data_rate: number;
  readonly danmu_count: number;
  readonly danmu_rate: number;
  readonly real_quality_number: QualityNumber;
  readonly postprocessor_status: PostprocessorStatus;
  readonly postprocessing_path: string | null;
  readonly postprocessing_progress: Progress | null;
}

export interface TaskParam {
  readonly out_dir: string;
  readonly path_template: string;
  readonly filesize_limit: number;
  readonly duration_limit: number;

  readonly user_agent: string;
  readonly cookie: string;

  readonly danmu_uname: boolean;

  readonly quality_number: QualityNumber;
  readonly read_timeout: number;
  readonly buffer_size: number;

  readonly remux_to_mp4: boolean;
  readonly delete_source: DeleteStrategy;
}

export enum VideoFileStatus {
  RECORDING = 'recording',
  REMUXING = 'remuxing',
  INJECTING = 'injecting',
  COMPLETED = 'completed',
  MISSING = 'missing',
  BROKEN = 'broken',
}

export enum DanmakuFileStatus {
  RECORDING = 'recording',
  COMPLETED = 'completed',
  MISSING = 'missing',
  BROKEN = 'broken',
}

export interface VideoFileDetail {
  readonly path: string;
  readonly size: number;
  readonly status: VideoFileStatus;
}

export interface DanmakuFileDetail {
  readonly path: string;
  readonly size: number;
  readonly status: DanmakuFileStatus;
}

export interface AddTaskResult extends ResponseMessage {
  data: {
    room_id: number;
  };
}
