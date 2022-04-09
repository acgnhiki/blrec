import { transform, isEqual, isObject } from 'lodash-es';

// ref: https://gist.github.com/Yimiprod/7ee176597fef230d1451
export function difference(object: object, base: object): object {
  function diff(object: object, base: object) {
    return transform(object, (result: object, value: any, key: string) => {
      const baseValue = Reflect.get(base, key);
      if (!isEqual(value, baseValue)) {
        Reflect.set(
          result,
          key,
          isObject(value) && isObject(baseValue)
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
    return '0 kbps/s';
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
    return '0B/s';
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
