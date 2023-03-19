import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { UrlService } from './url.service';

@Injectable({
  providedIn: 'root',
})
export class UpdateService {
  constructor(private http: HttpClient, private url: UrlService) {}

  getLatestVerisonString(): Observable<string> {
    const url = this.url.makeApiUrl(`/api/v1/update/version/latest`);
    return this.http.get<string>(url);
  }
}
