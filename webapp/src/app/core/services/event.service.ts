import { Injectable } from '@angular/core';

import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

import { environment } from 'src/environments/environment';
import { Event } from '../models/event.model';

const webSocketUrl = environment.webSocketUrl;

@Injectable({
  providedIn: 'root',
})
export class EventService {
  private eventSubject?: WebSocketSubject<Event>;

  constructor() {}

  get events() {
    if (!this.eventSubject) {
      this.eventSubject = webSocket(webSocketUrl + '/ws/v1/events');
    }
    return this.eventSubject;
  }
}
