import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'speed',
})
export class SpeedPipe implements PipeTransform {
  transform(rate: number, precision: number = 3): string {
    let num: number;
    let unit: string;

    if (rate <= 0) {
      return '0B/s';
    }

    if (rate < 1e3) {
      num = rate;
      unit = 'B';
    } else if (rate < 1e6) {
      num = rate / 1e3;
      unit = 'kB';
    } else if (rate < 1e9) {
      num = rate / 1e6;
      unit = 'MB';
    } else if (rate < 1e12) {
      num = rate / 1e9;
      unit = 'GB';
    } else {
      throw RangeError(`the rate argument ${rate} out of range`);
    }

    const digits = precision - Math.floor(Math.abs(Math.log10(num))) - 1;
    return num.toFixed(digits) + unit + '/s';
  }
}
