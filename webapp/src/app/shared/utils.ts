import { transform, isEqual, isObject } from 'lodash-es';
import * as filesize from 'filesize';

// ref: https://gist.github.com/Yimiprod/7ee176597fef230d1451
export function difference(
  object: object,
  base: object,
  deep: boolean = true
): object {
  function diff(object: object, base: object) {
    return transform(object, (result: object, value: any, key: string) => {
      const baseValue = Reflect.get(base, key);
      if (!isEqual(value, baseValue)) {
        Reflect.set(
          result,
          key,
          deep && isObject(value) && isObject(baseValue)
            ? diff(value, baseValue)
            : value
        );
      }
    });
  }
  return diff(object, base);
}

export function toBitRateString(
  bitrate: number,
  spacer: string = ' ',
  precision: number = 3
): string {
  let num: number;
  let unit: string;

  if (bitrate <= 0) {
    return '0' + spacer + 'kbps';
  }

  if (bitrate < 1e6) {
    num = bitrate / 1e3;
    unit = 'kbps';
  } else if (bitrate < 1e9) {
    num = bitrate / 1e6;
    unit = 'Mbps';
  } else if (bitrate < 1e12) {
    num = bitrate / 1e9;
    unit = 'Gbps';
  } else if (bitrate < 1e15) {
    num = bitrate / 1e12;
    unit = 'Tbps';
  } else {
    throw RangeError(`the rate argument ${bitrate} out of range`);
  }

  const digits = precision - Math.floor(Math.abs(Math.log10(num))) - 1;
  return num.toFixed(digits < 0 ? 0 : digits) + spacer + unit;
}

export function toByteRateString(
  rate: number,
  spacer: string = ' ',
  precision: number = 3
): string {
  let num: number;
  let unit: string;

  if (rate <= 0) {
    return '0' + spacer + 'B/s';
  }

  if (rate < 1e3) {
    num = rate;
    unit = 'B/s';
  } else if (rate < 1e6) {
    num = rate / 1e3;
    unit = 'KB/s';
  } else if (rate < 1e9) {
    num = rate / 1e6;
    unit = 'MB/s';
  } else if (rate < 1e12) {
    num = rate / 1e9;
    unit = 'GB/s';
  } else if (rate < 1e15) {
    num = rate / 1e12;
    unit = 'TB/s';
  } else {
    throw RangeError(`the rate argument ${rate} out of range`);
  }

  const digits = precision - Math.floor(Math.abs(Math.log10(num))) - 1;
  return num.toFixed(digits < 0 ? 0 : digits) + spacer + unit;
}

export function formatDuration(
  totalSeconds: number,
  concise: boolean = false
): string {
  if (!(totalSeconds > 0)) {
    totalSeconds = 0;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const seconds = Math.floor(totalSeconds % 60);

  let result = '';

  if (concise) {
    if (hours > 0) {
      result += hours + ':';
    }
  } else {
    result += hours < 10 ? '0' + hours : hours;
    result += ':';
  }
  result += minutes < 10 ? '0' + minutes : minutes;
  result += ':';
  result += seconds < 10 ? '0' + seconds : seconds;

  return result;
}

export function parseDuration(str: string): number | null {
  try {
    const [_, hours, minutes, seconds] = /(\d{1,2}):(\d{2}):(\d{2})/.exec(str)!;
    return parseInt(hours) * 3600 + parseInt(minutes) * 60 + parseInt(seconds);
  } catch (error) {
    console.error(`Failed to parse duration: ${str}`, error);
    return null;
  }
}

export function formatFilesize(size: number): string {
  return filesize(size);
}

export function parseFilesize(str: string): number | null {
  try {
    const [_, num, unit] = /^(\d+(?:\.\d+)?)\s*([TGMK]?B)$/.exec(str)!;
    switch (unit) {
      case 'B':
        return parseFloat(num);
      case 'KB':
        return 1024 ** 1 * parseFloat(num);
      case 'MB':
        return 1024 ** 2 * parseFloat(num);
      case 'GB':
        return 1024 ** 3 * parseFloat(num);
      case 'TB':
        return 1024 ** 4 * parseFloat(num);
      default:
        console.warn(`Unexpected unit: ${unit}`, str);
        return null;
    }
  } catch (error) {
    console.error(`Failed to parse filesize: ${str}`, error);
    return null;
  }
}
