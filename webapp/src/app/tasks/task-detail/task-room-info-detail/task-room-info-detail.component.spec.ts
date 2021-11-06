import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskRoomInfoDetailComponent } from './task-room-info-detail.component';

describe('TaskRoomInfoDetailComponent', () => {
  let component: TaskRoomInfoDetailComponent;
  let fixture: ComponentFixture<TaskRoomInfoDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskRoomInfoDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskRoomInfoDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
