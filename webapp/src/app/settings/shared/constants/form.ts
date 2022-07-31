import { CoverSaveStrategy, DeleteStrategy } from '../setting.model';

import range from 'lodash-es/range';

export const SPLIT_FILE_TIP = '会按照此限制自动分割文件';
export const SYNC_FAILED_WARNING_TIP = '设置同步失败！';

export const PATH_TEMPLATE_PATTERN =
  /^(?:[^\\\/:*?"<>|\t\n\r\f\v\{\}]*?\{(?:roomid|uname|title|area|parent_area|year|month|day|hour|minute|second)\}[^\\\/:*?"<>|\t\n\r\f\v\{\}]*?)+?(?:\/(?:[^\\\/:*?"<>|\t\n\r\f\v\{\}]*?\{(?:roomid|uname|title|area|parent_area|year|month|day|hour|minute|second)\}[^\\\/:*?"<>|\t\n\r\f\v\{\}]*?)+?)*$/;

export const PATH_TEMPLATE_DEFAULT =
  '{roomid} - {uname}/blive_{roomid}_{year}-{month}-{day}-{hour}{minute}{second}';

export type PathTemplateVariable = {
  name: string;
  desc: string;
};

export const PATH_TEMPLATE_VARIABLES: Readonly<PathTemplateVariable[]> = [
  { name: 'roomid', desc: '房间号' },
  { name: 'uname', desc: '主播用户名' },
  { name: 'title', desc: '房间标题' },
  { name: 'area', desc: '直播子分区名称' },
  { name: 'parent_area', desc: '直播主分区名称' },
  { name: 'year', desc: '文件创建日期时间之年份' },
  { name: 'month', desc: '文件创建日期时间之月份' },
  { name: 'day', desc: '文件创建日期时间之天数' },
  { name: 'hour', desc: '文件创建日期时间之小时' },
  { name: 'minute', desc: '文件创建日期时间之分钟' },
  { name: 'second', desc: '文件创建日期时间之秒数' },
] as const;

export const FILESIZE_LIMIT_OPTIONS = [
  { label: '不限', value: 0 },
  ...range(1, 21).map((i) => ({
    label: `${i} GB`,
    value: 1024 ** 3 * i,
  })),
] as const;

export const DURATION_LIMIT_OPTIONS = [
  { label: '不限', value: 0 },
  ...range(1, 25).map((i) => ({
    label: `${i} 小时`,
    value: 3600 * i,
  })),
] as const;

export const DELETE_STRATEGIES = [
  { label: '自动', value: DeleteStrategy.AUTO },
  { label: '谨慎', value: DeleteStrategy.SAFE },
  { label: '从不', value: DeleteStrategy.NEVER },
] as const;

export const COVER_SAVE_STRATEGIES = [
  { label: '默认', value: CoverSaveStrategy.DEFAULT },
  { label: '去重', value: CoverSaveStrategy.DEDUP },
] as const;

export const STREAM_FORMAT_OPTIONS = [
  { label: 'FLV', value: 'flv' },
  // { label: 'HLS (ts)', value: 'ts' },
  { label: 'HLS (fmp4)', value: 'fmp4' },
] as const;

export const RECORDING_MODE_OPTIONS = [
  { label: '标准', value: 'standard' },
  { label: '原始', value: 'raw' },
] as const;

export const QUALITY_OPTIONS = [
  { label: '4K', value: 20000 },
  { label: '原画', value: 10000 },
  { label: '蓝光(杜比)', value: 401 },
  { label: '蓝光', value: 400 },
  { label: '超清', value: 250 },
  { label: '高清', value: 150 },
  { label: '流畅', value: 80 },
] as const;

export const TIMEOUT_OPTIONS = [
  { label: '3 秒', value: 3 },
  { label: '5 秒', value: 5 },
  { label: '10 秒', value: 10 },
  { label: '30 秒', value: 30 },
  { label: '1 分钟', value: 60 },
  { label: '3 分钟', value: 180 },
  { label: '5 分钟', value: 300 },
  { label: '10 分钟', value: 600 },
] as const;

export const DISCONNECTION_TIMEOUT_OPTIONS = [
  { label: '3 分钟', value: 3 * 60 },
  { label: '5 分钟', value: 5 * 60 },
  { label: '10 分钟', value: 10 * 60 },
  { label: '15 分钟', value: 15 * 60 },
  { label: '20 分钟', value: 20 * 60 },
  { label: '30 分钟', value: 30 * 60 },
] as const;

export const BUFFER_OPTIONS = [
  { label: '4 KB', value: 1024 * 4 },
  { label: '8 KB', value: 1024 * 8 },
  { label: '16 KB', value: 1024 * 16 },
  { label: '32 KB', value: 1024 * 32 },
  { label: '64 KB', value: 1024 * 64 },
  { label: '128 KB', value: 1024 * 128 },
  { label: '256 KB', value: 1024 * 256 },
  { label: '512 KB', value: 1024 * 512 },
  { label: '1 MB', value: 1024 ** 2 },
  { label: '2 MB', value: 1024 ** 2 * 2 },
  { label: '4 MB', value: 1024 ** 2 * 4 },
  { label: '8 MB', value: 1024 ** 2 * 8 },
  { label: '16 MB', value: 1024 ** 2 * 16 },
  { label: '32 MB', value: 1024 ** 2 * 32 },
  { label: '64 MB', value: 1024 ** 2 * 64 },
  { label: '128 MB', value: 1024 ** 2 * 128 },
  { label: '256 MB', value: 1024 ** 2 * 256 },
  { label: '512 MB', value: 1024 ** 2 * 512 },
] as const;
