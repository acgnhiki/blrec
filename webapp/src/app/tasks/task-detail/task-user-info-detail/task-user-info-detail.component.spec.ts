import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskUserInfoDetailComponent } from './task-user-info-detail.component';

describe('TaskUserInfoDetailComponent', () => {
  let component: TaskUserInfoDetailComponent;
  let fixture: ComponentFixture<TaskUserInfoDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskUserInfoDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskUserInfoDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
