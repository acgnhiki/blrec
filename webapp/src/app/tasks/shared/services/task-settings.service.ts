import { Injectable } from '@angular/core';

import { StorageService } from 'src/app/core/services/storage.service';

export interface TaskSettings {
  showInfoPanel?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class TaskSettingsService {
  constructor(private storage: StorageService) {}

  getSettings(roomId: number): TaskSettings {
    const settingsString = this.storage.getData(this.getStorageKey(roomId));
    if (settingsString) {
      return JSON.parse(settingsString) ?? {};
    } else {
      return {};
    }
  }

  updateSettings(roomId: number, settings: TaskSettings): void {
    settings = Object.assign(this.getSettings(roomId), settings);
    const settingsString = JSON.stringify(settings);
    this.storage.setData(this.getStorageKey(roomId), settingsString);
  }

  private getStorageKey(roomId: number): string {
    return `app-tasks-${roomId}`;
  }
}
