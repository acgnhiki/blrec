import type { Nullable, PartialDeep } from 'src/app/shared/utility-types';

export interface BiliApiSettings {
  baseApiUrls: string[];
  baseLiveApiUrls: string[];
  basePlayInfoApiUrls: string[];
}

export type BiliApiOptions = Nullable<BiliApiSettings>;

export interface HeaderSettings {
  userAgent: string;
  cookie: string;
}

export type HeaderOptions = Nullable<HeaderSettings>;

export interface DanmakuSettings {
  danmuUname: boolean;
  recordGiftSend: boolean;
  recordFreeGifts: boolean;
  recordGuardBuy: boolean;
  recordSuperChat: boolean;
  saveRawDanmaku: boolean;
}

export type DanmakuOptions = Nullable<DanmakuSettings>;

export type StreamFormat = 'flv' | 'ts' | 'fmp4';
export type RecordingMode = 'standard' | 'raw';

export type QualityNumber =
  | 20000 // 4K
  | 10000 // 原画
  | 401 // 蓝光(杜比)
  | 400 // 蓝光
  | 250 // 超清
  | 150 // 高清
  | 80; // 流畅

export enum CoverSaveStrategy {
  DEFAULT = 'default',
  DEDUP = 'dedup',
}

export interface RecorderSettings {
  streamFormat: StreamFormat;
  recordingMode: RecordingMode;
  qualityNumber: QualityNumber;
  fmp4StreamTimeout: number;
  readTimeout: number;
  disconnectionTimeout: number;
  bufferSize: number;
  saveCover: boolean;
  coverSaveStrategy: CoverSaveStrategy;
}

export type RecorderOptions = Nullable<RecorderSettings>;

export enum DeleteStrategy {
  AUTO = 'auto',
  SAFE = 'safe',
  NEVER = 'never',
}

export interface PostprocessingSettings {
  injectExtraMetadata: boolean;
  remuxToMp4: boolean;
  deleteSource: DeleteStrategy;
}

export type PostprocessingOptions = Nullable<PostprocessingSettings>;

export interface TaskOptions {
  output: OutputOptions;
  biliApi: BiliApiOptions;
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
  'output' | 'biliApi' | 'header' | 'danmaku' | 'recorder' | 'postprocessing'
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
  logDir: string;
  consoleLogLevel: LogLevel;
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

export interface PushdeerSettings {
  server: string;
  pushkey: string;
}

export const KEYS_OF_PUSHDEER_SETTINGS = ['server', 'pushkey'] as const;

export interface PushplusSettings {
  token: string;
  topic: string;
}

export const KEYS_OF_PUSHPLUS_SETTINGS = ['token', 'topic'] as const;

export interface TelegramSettings {
  token: string;
  chatid: string;
  server: string;
}

export const KEYS_OF_TELEGRAM_SETTINGS = ['token', 'chatid', 'server'] as const;

export interface NotifierSettings {
  enabled: boolean;
}
export interface BarkSettings {
  server: string;
  pushkey: string;
}

export const KEYS_OF_BARK_SETTINGS = ['server', 'pushkey'] as const;

export interface PushplusSettings {
  token: string;
  topic: string;
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

export type TextMessageType = 'text';
export type HtmlMessageType = 'html';
export type MarkdownMessageType = 'markdown';
export type MessageType =
  | TextMessageType
  | MarkdownMessageType
  | HtmlMessageType;

export type EmailMessageType = TextMessageType | HtmlMessageType;
export type ServerchanMessageType = MarkdownMessageType;
export type PushdeerMessageType = TextMessageType | MarkdownMessageType;
export type PushplusMessageType =
  | TextMessageType
  | MarkdownMessageType
  | HtmlMessageType;
export type TelegramMessageType = MarkdownMessageType | HtmlMessageType;
export type BarkMessageType = TextMessageType;


export interface MessageTemplateSettings {
  beganMessageType: string;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: string;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: string;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: string;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export const KEYS_OF_MESSAGE_TEMPLATE_SETTINGS = [
  'beganMessageType',
  'beganMessageTitle',
  'beganMessageContent',
  'endedMessageType',
  'endedMessageTitle',
  'endedMessageContent',
  'spaceMessageType',
  'spaceMessageTitle',
  'spaceMessageContent',
  'errorMessageType',
  'errorMessageTitle',
  'errorMessageContent',
] as const;

export interface EmailMessageTemplateSettings {
  beganMessageType: EmailMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: EmailMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: EmailMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: EmailMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export interface ServerchanMessageTemplateSettings {
  beganMessageType: ServerchanMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: ServerchanMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: ServerchanMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: ServerchanMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export interface PushdeerMessageTemplateSettings {
  beganMessageType: PushdeerMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: PushdeerMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: PushdeerMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: PushdeerMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export interface PushplusMessageTemplateSettings {
  beganMessageType: PushplusMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: PushplusMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: PushplusMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: PushplusMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export interface TelegramMessageTemplateSettings {
  beganMessageType: PushplusMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: PushplusMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: PushplusMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: PushplusMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}
export interface BarkMessageTemplateSettings {
  beganMessageType: BarkMessageType;
  beganMessageTitle: string;
  beganMessageContent: string;
  endedMessageType: BarkMessageType;
  endedMessageTitle: string;
  endedMessageContent: string;
  spaceMessageType: BarkMessageType;
  spaceMessageTitle: string;
  spaceMessageContent: string;
  errorMessageType: BarkMessageType;
  errorMessageTitle: string;
  errorMessageContent: string;
}

export type EmailNotificationSettings = EmailSettings &
  NotifierSettings &
  NotificationSettings &
  EmailMessageTemplateSettings;

export type ServerchanNotificationSettings = ServerchanSettings &
  NotifierSettings &
  NotificationSettings &
  ServerchanMessageTemplateSettings;

export type PushdeerNotificationSettings = PushdeerSettings &
  NotifierSettings &
  NotificationSettings &
  PushdeerMessageTemplateSettings;

export type PushplusNotificationSettings = PushplusSettings &
  NotifierSettings &
  NotificationSettings &
  PushdeerMessageTemplateSettings;

export type TelegramNotificationSettings = TelegramSettings &
  NotifierSettings &
  NotificationSettings &
  TelegramMessageTemplateSettings;

export type BarkNotificationSettings = BarkSettings &
  NotifierSettings &
  NotificationSettings &
  BarkMessageTemplateSettings;

export interface WebhookEventSettings {
  liveBegan: boolean;
  liveEnded: boolean;
  roomChange: boolean;
  recordingStarted: boolean;
  recordingFinished: boolean;
  recordingCancelled: boolean;
  videoFileCreated: boolean;
  videoFileCompleted: boolean;
  danmakuFileCreated: boolean;
  danmakuFileCompleted: boolean;
  rawDanmakuFileCreated: boolean;
  rawDanmakuFileCompleted: boolean;
  videoPostprocessingCompleted: boolean;
  spaceNoEnough: boolean;
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
  biliApi: BiliApiSettings;
  header: HeaderSettings;
  danmaku: DanmakuSettings;
  recorder: RecorderSettings;
  postprocessing: PostprocessingSettings;
  space: SpaceSettings;
  emailNotification: EmailNotificationSettings;
  serverchanNotification: ServerchanNotificationSettings;
  pushdeerNotification: PushdeerNotificationSettings;
  pushplusNotification: PushplusNotificationSettings;
  telegramNotification: TelegramNotificationSettings;
  barkNotification: BarkNotificationSettings;
  webhooks: WebhookSettings[];
}

export type SettingsIn = PartialDeep<Omit<Settings, 'version' | 'tasks'>>;
export type SettingsOut = Partial<Settings>;
