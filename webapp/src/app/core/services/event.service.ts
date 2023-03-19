import { Injectable } from '@angular/core';

import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

import { Event } from '../models/event.model';
import { UrlService } from './url.service';

@Injectable({
  providedIn: 'root',
})
export class EventService {
  private eventSubject?: WebSocketSubject<Event>;

  constructor(private url: UrlService) {}

  get events() {
    if (!this.eventSubject) {
      this.eventSubject = webSocket(this.url.makeWebSocketUrl('/ws/v1/events'));
    }
    return this.eventSubject;
  }
}
