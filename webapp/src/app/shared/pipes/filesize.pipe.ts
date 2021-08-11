import { Pipe, PipeTransform } from '@angular/core';

import * as filesize from 'filesize';

@Pipe({
  name: 'filesize',
})
export class FilesizePipe implements PipeTransform {
  transform(size: number, options?: Parameters<typeof filesize>[1]): string {
    return filesize(size, options);
  }
}
