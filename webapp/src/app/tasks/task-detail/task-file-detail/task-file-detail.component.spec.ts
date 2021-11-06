import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskFileDetailComponent } from './task-file-detail.component';

describe('TaskFileDetailComponent', () => {
  let component: TaskFileDetailComponent;
  let fixture: ComponentFixture<TaskFileDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskFileDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskFileDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
