import { Pipe, PipeTransform } from '@angular/core';

import { filesize } from 'filesize';

@Pipe({
  name: 'filesize',
})
export class FilesizePipe implements PipeTransform {
  transform(size: number, options?: Parameters<typeof filesize>[1]): string {
    return filesize(size, {
      base: 2,
      standard: 'jedec',
      ...options,
      output: 'string',
    }) as string;
  }
}
