import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { environment } from 'src/environments/environment';

const apiUrl = environment.apiUrl;

@Injectable({
  providedIn: 'root',
})
export class UpdateService {
  constructor(private http: HttpClient) {}

  getLatestVerisonString(): Observable<string> {
    const url = apiUrl + `/api/v1/update/version/latest`;
    return this.http.get<string>(url);
  }
}
