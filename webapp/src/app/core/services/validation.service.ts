import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { environment } from 'src/environments/environment';
import { ResponseMessage } from 'src/app/shared/api.models';

const apiUrl = environment.apiUrl;

@Injectable({
  providedIn: 'root',
})
export class ValidationService {
  constructor(private http: HttpClient) {}

  validateDir(path: string): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/validation/dir`;
    return this.http.post<ResponseMessage>(url, { path });
  }
}
