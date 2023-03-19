import { Injectable } from '@angular/core';

import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

import { Event } from '../models/event.model';
import { UrlService } from './url.service';

@Injectable({
  providedIn: 'root',
})
export class ExceptionService {
  private exceptionSubject?: WebSocketSubject<Event>;

  constructor(private url: UrlService) {}

  get exceptions() {
    if (!this.exceptionSubject) {
      this.exceptionSubject = webSocket(
        this.url.makeWebSocketUrl('/ws/v1/exceptions')
      );
    }
    return this.exceptionSubject;
  }
}
