import { Pipe, PipeTransform } from '@angular/core';

import { QualityNumber } from 'src/app/settings/shared/setting.model';
import { QUALITY_NAME_MAPPING } from '../constants';

@Pipe({
  name: 'quality',
})
export class QualityPipe implements PipeTransform {
  transform(qualityNumber: QualityNumber): string {
    return QUALITY_NAME_MAPPING[qualityNumber];
  }
}
