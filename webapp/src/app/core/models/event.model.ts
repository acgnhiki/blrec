import { RoomInfo, UserInfo } from 'src/app/tasks/shared/task.model';

export type Event =
  | LiveBeganEvent
  | LiveEndedEvent
  | RoomChangeEvent
  | SpaceNoEnoughEvent
  | FilesAvailableEvent;

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

export interface SpaceNoEnoughEvent {
  readonly type: 'SpaceNoEnoughEvent';
  readonly data: {
    path: string;
    threshold: number;
    usage: DiskUsage;
  };
}

export interface FilesAvailableEvent {
  readonly type: 'FilesAvailableEvent';
  readonly data: {
    files: string[];
  };
}

export interface DiskUsage {
  total: number;
  used: number;
  free: number;
}
