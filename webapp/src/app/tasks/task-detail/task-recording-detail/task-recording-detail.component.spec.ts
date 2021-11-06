import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskRecordingDetailComponent } from './task-recording-detail.component';

describe('TaskRecordingDetailComponent', () => {
  let component: TaskRecordingDetailComponent;
  let fixture: ComponentFixture<TaskRecordingDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskRecordingDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskRecordingDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
