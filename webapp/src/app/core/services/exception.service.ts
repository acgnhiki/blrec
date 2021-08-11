import { Injectable } from '@angular/core';

import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

import { environment } from 'src/environments/environment';
import { Event } from '../models/event.model';

const webSocketUrl = environment.webSocketUrl;

@Injectable({
  providedIn: 'root'
})
export class ExceptionService {
  private exceptionSubject?: WebSocketSubject<Event>;

  constructor() {}

  get exceptions() {
    if (!this.exceptionSubject) {
      this.exceptionSubject = webSocket(webSocketUrl + '/ws/v1/exceptions');
    }
    return this.exceptionSubject;
  }
}
