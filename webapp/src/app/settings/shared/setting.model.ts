import type { Nullable, PartialDeep } from 'src/app/shared/utility-types';

export interface HeaderSettings {
  userAgent: string;
  cookie: string;
}

export type HeaderOptions = Nullable<HeaderSettings>;

export interface DanmakuSettings {
  danmuUname: boolean;
}

export type DanmakuOptions = Nullable<DanmakuSettings>;

export type QualityNumber =
  | 20000 // 4K
  | 10000 // 原画
  | 401 // 蓝光(杜比)
  | 400 // 蓝光
  | 250 // 超清
  | 150 // 高清
  | 80; // 流畅

export interface RecorderSettings {
  qualityNumber: QualityNumber;
  readTimeout: number;
  bufferSize: number;
}

export type RecorderOptions = Nullable<RecorderSettings>;

export enum DeleteStrategy {
  AUTO = 'auto',
  NEVER = 'never',
}

export interface PostprocessingSettings {
  remuxToMp4: boolean;
  deleteSource: DeleteStrategy;
}

export type PostprocessingOptions = Nullable<PostprocessingSettings>;

export interface TaskOptions {
  output: OutputOptions;
  header: HeaderOptions;
  danmaku: DanmakuOptions;
  recorder: RecorderOptions;
  postprocessing: PostprocessingOptions;
}

export type TaskOptionsIn = PartialDeep<TaskOptions>;

export interface TaskSettings extends TaskOptions {
  roomId: number;
  enableMonitor: boolean;
  enableRecorder: boolean;
}

export type GlobalTaskSettings = Pick<
  Settings,
  'output' | 'header' | 'danmaku' | 'recorder' | 'postprocessing'
>;

export interface OutputSettings {
  outDir: string;
  pathTemplate: string;
  filesizeLimit: number;
  durationLimit: number;
}

export type OutputOptions = Nullable<Omit<OutputSettings, 'outDir'>>;

export type LogLevel =
  | 'CRITICAL'
  | 'ERROR'
  | 'WARNING'
  | 'INFO'
  | 'DEBUG'
  | 'NOTSET';

export interface LoggingSettings {
  consoleLogLevel: LogLevel;
  maxBytes: number;
  backupCount: number;
}

export interface SpaceSettings {
  checkInterval: number;
  spaceThreshold: number;
  recycleRecords: boolean;
}

export interface EmailSettings {
  srcAddr: string;
  dstAddr: string;
  authCode: string;
  smtpHost: string;
  smtpPort: number;
}

export const KEYS_OF_EMAIL_SETTINGS = [
  'srcAddr',
  'dstAddr',
  'authCode',
  'smtpHost',
  'smtpPort',
] as const;

export interface ServerchanSettings {
  sendkey: string;
}

export const KEYS_OF_SERVERCHAN_SETTINGS = ['sendkey'] as const;

export interface PushplusSettings {
  token: string;
  topic: string;
}

export const KEYS_OF_PUSHPLUS_SETTINGS = ['token', 'topic'] as const;

export interface NotifierSettings {
  enabled: boolean;
}

export const KEYS_OF_NOTIFIER_SETTINGS = ['enabled'] as const;

export interface NotificationSettings {
  notifyBegan: boolean;
  notifyEnded: boolean;
  notifyError: boolean;
  notifySpace: boolean;
}

export const KEYS_OF_NOTIFICATION_SETTINGS = [
  'notifyBegan',
  'notifyEnded',
  'notifyError',
  'notifySpace',
] as const;

export type EmailNotificationSettings = EmailSettings &
  NotifierSettings &
  NotificationSettings;

export type ServerchanNotificationSettings = ServerchanSettings &
  NotifierSettings &
  NotificationSettings;

export type PushplusNotificationSettings = PushplusSettings &
  NotifierSettings &
  NotificationSettings;

export interface WebhookEventSettings {
  liveBegan: boolean;
  liveEnded: boolean;
  roomChange: boolean;
  spaceNoEnough: boolean;
  fileCompleted: boolean;
  errorOccurred: boolean;
}

export interface WebhookSettings extends WebhookEventSettings {
  url: string;
}

export interface Settings {
  version: string;
  tasks: TaskSettings[];
  output: OutputSettings;
  logging: LoggingSettings;
  header: HeaderSettings;
  danmaku: DanmakuSettings;
  recorder: RecorderSettings;
  postprocessing: PostprocessingSettings;
  space: SpaceSettings;
  emailNotification: EmailNotificationSettings;
  serverchanNotification: ServerchanNotificationSettings;
  pushplusNotification: PushplusNotificationSettings;
  webhooks: WebhookSettings[];
}

export type SettingsIn = PartialDeep<Omit<Settings, 'version' | 'tasks'>>;
export type SettingsOut = Partial<Settings>;
