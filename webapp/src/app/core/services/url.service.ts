import { Injectable } from '@angular/core';
import { Location } from '@angular/common';

import { environment } from 'src/environments/environment';

const API_BASE_URL = environment.apiBaseUrl;
const WEB_SOCKET_BASE_URL = environment.webSocketBaseUrl;

@Injectable({
  providedIn: 'root',
})
export class UrlService {
  constructor(private location: Location) {}

  makeApiUrl(uri: string): string {
    return API_BASE_URL + this.location.prepareExternalUrl(uri);
  }

  makeWebSocketUrl(uri: string): string {
    return WEB_SOCKET_BASE_URL + this.location.prepareExternalUrl(uri);
  }
}
