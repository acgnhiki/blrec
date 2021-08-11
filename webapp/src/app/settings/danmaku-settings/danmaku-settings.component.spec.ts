import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DanmakuSettingsComponent } from './danmaku-settings.component';

describe('DanmakuSettingsComponent', () => {
  let component: DanmakuSettingsComponent;
  let fixture: ComponentFixture<DanmakuSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DanmakuSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DanmakuSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
