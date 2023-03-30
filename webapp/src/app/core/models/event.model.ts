import { RoomInfo, UserInfo } from 'src/app/tasks/shared/task.model';

export type Event =
  | LiveBeganEvent
  | LiveEndedEvent
  | RoomChangeEvent
  | RecordingStartedEvent
  | RecordingFinishedEvent
  | RecordingCancelledEvent
  | VideoFileCreatedEvent
  | VideoFileCompletedEvent
  | DanmakuFileCreatedEvent
  | DanmakuFileCompletedEvent
  | RawDanmakuFileCreatedEvent
  | RawDanmakuFileCompletedEvent
  | CoverImageDownloadedEvent
  | SpaceNoEnoughEvent
  | VideoPostprocessingCompletedEvent
  | PostprocessingCompletedEvent;

export interface LiveBeganEvent {
  readonly type: 'LiveBeganEvent';
  readonly data: {
    readonly user_info: UserInfo;
    readonly room_info: RoomInfo;
  };
}

export interface LiveEndedEvent {
  readonly type: 'LiveEndedEvent';
  readonly data: {
    readonly user_info: UserInfo;
    readonly room_info: RoomInfo;
  };
}

export interface RoomChangeEvent {
  readonly type: 'RoomChangeEvent';
  readonly data: {
    readonly room_info: RoomInfo;
  };
}
export interface RecordingStartedEvent {
  readonly type: 'RecordingStartedEvent';
  readonly data: {
    readonly room_info: RoomInfo;
  };
}
export interface RecordingFinishedEvent {
  readonly type: 'RecordingFinishedEvent';
  readonly data: {
    readonly room_info: RoomInfo;
  };
}

export interface RecordingCancelledEvent {
  readonly type: 'RecordingCancelledEvent';
  readonly data: {
    readonly room_info: RoomInfo;
  };
}
export interface VideoFileCreatedEvent {
  readonly type: 'VideoFileCreatedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}
export interface VideoFileCompletedEvent {
  readonly type: 'VideoFileCompletedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}
export interface DanmakuFileCreatedEvent {
  readonly type: 'DanmakuFileCreatedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}
export interface DanmakuFileCompletedEvent {
  readonly type: 'DanmakuFileCompletedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}
export interface RawDanmakuFileCreatedEvent {
  readonly type: 'RawDanmakuFileCreatedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}
export interface RawDanmakuFileCompletedEvent {
  readonly type: 'RawDanmakuFileCompletedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}

export interface CoverImageDownloadedEvent {
  readonly type: 'CoverImageDownloadedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}

export interface VideoPostprocessingCompletedEvent {
  readonly type: 'VideoPostprocessingCompletedEvent';
  readonly data: {
    room_id: number;
    path: string;
  };
}

export interface PostprocessingCompletedEvent {
  readonly type: 'PostprocessingCompletedEvent';
  readonly data: {
    room_id: number;
    files: string[];
  };
}

export interface SpaceNoEnoughEvent {
  readonly type: 'SpaceNoEnoughEvent';
  readonly data: {
    path: string;
    threshold: number;
    usage: DiskUsage;
  };
}

export interface DiskUsage {
  total: number;
  used: number;
  free: number;
}
