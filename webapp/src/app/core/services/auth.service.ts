import { Injectable } from '@angular/core';
import { StorageService } from './storage.service';

const API_KEY_STORAGE_KEY = 'app-api-key';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  constructor(private storage: StorageService) {}

  hasApiKey(): boolean {
    return this.storage.hasData(API_KEY_STORAGE_KEY);
  }

  getApiKey(): string {
    return this.storage.getData(API_KEY_STORAGE_KEY) ?? '';
  }

  setApiKey(value: string): void {
    this.storage.setData(API_KEY_STORAGE_KEY, value);
  }

  removeApiKey() {
    this.storage.removeData(API_KEY_STORAGE_KEY);
  }
}
