import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class StorageService {
  private impl = localStorage;

  constructor() {}

  hasData(key: string): boolean {
    return this.getData(key) !== null;
  }

  getData(key: string): string | null {
    return this.impl.getItem(key);
  }

  setData(key: string, value: string): void {
    this.impl.setItem(key, value);
  }

  removeData(key: string): void {
    this.impl.removeItem(key);
  }

  clearData(): void {
    this.impl.clear();
  }
}
