import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { ResponseMessage } from 'src/app/shared/api.models';
import { UrlService } from './url.service';

@Injectable({
  providedIn: 'root',
})
export class ValidationService {
  constructor(private http: HttpClient, private url: UrlService) {}

  validateDir(path: string): Observable<ResponseMessage> {
    const url = this.url.makeApiUrl(`/api/v1/validation/dir`);
    return this.http.post<ResponseMessage>(url, { path });
  }

  validateCookie(cookie: string): Observable<ResponseMessage> {
    const url = this.url.makeApiUrl(`/api/v1/validation/cookie`);
    return this.http.post<ResponseMessage>(url, { cookie });
  }
}
