import { Pipe, PipeTransform } from '@angular/core';

import { toBitRateString, toByteRateString } from '../utils';

@Pipe({
  name: 'datarate',
})
export class DataratePipe implements PipeTransform {
  transform(
    rate: number | string,
    options?: {
      bitrate?: boolean;
      precision?: number;
      spacer?: string;
    }
  ): string {
    if (typeof rate === 'string') {
      rate = parseFloat(rate);
    } else if (typeof rate === 'number' && !isNaN(rate)) {
      // pass
    } else {
      return 'N/A';
    }
    options = Object.assign(
      {
        bitrate: false,
        precision: 3,
        spacer: ' ',
      },
      options
    );
    if (options.bitrate) {
      return toBitRateString(rate, options.spacer, options.precision);
    } else {
      return toByteRateString(rate, options.spacer, options.precision);
    }
  }
}
