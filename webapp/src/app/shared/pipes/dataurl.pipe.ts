import { Pipe, PipeTransform } from '@angular/core';
import { SafeUrl, DomSanitizer } from '@angular/platform-browser';

import { from, fromEvent, Observable, of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

const dataUrlCache = new Map<string, SafeUrl>();
const objectUrlCache = new Map<string, SafeUrl>();

@Pipe({
  name: 'dataurl',
})
export class DataurlPipe implements PipeTransform {
  constructor(private domSanitizer: DomSanitizer) {}

  transform(
    url: string,
    type: 'object' | 'data' = 'object'
  ): Observable<SafeUrl> {
    if (type === 'object') {
      if (objectUrlCache.has(url)) {
        return of(objectUrlCache.get(url)!);
      }
      return from(this.fetchImage(url)).pipe(
        map((data) => URL.createObjectURL(data)),
        map((objectUrl) => this.domSanitizer.bypassSecurityTrustUrl(objectUrl)),
        tap((objectSafeUrl) => objectUrlCache.set(url, objectSafeUrl)),
        catchError(() => of(this.domSanitizer.bypassSecurityTrustUrl('')))
      );
    } else {
      if (dataUrlCache.has(url)) {
        return of(dataUrlCache.get(url)!);
      }
      return from(this.fetchImage(url)).pipe(
        switchMap((data) => this.createDataURL(data)),
        tap((dataUrl) => dataUrlCache.set(url, dataUrl)),
        catchError(() => of(this.domSanitizer.bypassSecurityTrustUrl('')))
      );
    }
  }

  private async fetchImage(url: string): Promise<Blob> {
    const res = await fetch(url, { referrer: '' });
    return await res.blob();
  }

  private createDataURL(data: Blob): Observable<SafeUrl> {
    const reader = new FileReader();
    const observable = fromEvent(reader, 'load').pipe(
      map(() =>
        this.domSanitizer.bypassSecurityTrustUrl(reader.result as string)
      )
    );
    reader.readAsDataURL(data);
    return observable;
  }
}
